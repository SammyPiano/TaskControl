from decimal import Decimal, InvalidOperation

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.mixins import filtrar_por_usuario
from gestion_campo.api import EmpresaActiva, EsAdministrador, EsEmpleado, monto, persona, servir_archivo
from tareas.models import Tarea

from .forms import GastoForm
from .models import CERO, Gasto, Liquidacion, Viatico


def viaticos_visibles(usuario):
    """Regla 5: el empleado solo los suyos; el administrador, los de su empresa."""
    return filtrar_por_usuario(Viatico.objects.all(), usuario, "tarea__empresa", "empleado").select_related(
        "tarea", "empleado"
    )


def decimal(valor, opcional=False):
    if valor in (None, "") and opcional:
        return CERO
    try:
        return Decimal(str(valor).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def tarea_corta(t):
    return {"id": t.pk, "codigo": t.codigo, "titulo": t.titulo, "ubicacion": t.ubicacion}


def viatico_resumen(v):
    return {
        "id": v.pk,
        "codigo": v.codigo,
        "concepto": v.concepto,
        "estado": v.estado,
        "estado_display": v.get_estado_display(),
        "tarea": tarea_corta(v.tarea),
        "empleado": persona(v.empleado),
        "monto_solicitado": monto(v.monto_solicitado),
        "monto_aprobado": monto(v.monto_aprobado),
        "anticipo_entregado": monto(v.anticipo_entregado),
        "solicitado_en": v.solicitado_en,
    }


def resultado(saldo):
    if saldo > 0:
        return Liquidacion.Resultado.REEMBOLSO
    return Liquidacion.Resultado.DEVOLUCION if saldo < 0 else Liquidacion.Resultado.SALDADO


def viatico_detalle(v):
    totales = v.totales()
    saldo = totales[Gasto.Estado.APROBADO] - v.anticipo_entregado
    liquidacion = getattr(v, "liquidacion", None)
    return {
        **viatico_resumen(v),
        "observacion": v.observacion,
        "autorizado_por": persona(v.autorizado_por),
        "autorizado_en": v.autorizado_en,
        "admite_gastos": v.admite_gastos,
        "totales": {estado.lower(): monto(valor) for estado, valor in totales.items()},
        # Regla 6: vista previa de la liquidación con los gastos ya aprobados
        "saldo": monto(saldo),
        "resultado_previsto": Liquidacion.Resultado(resultado(saldo)).label,
        "gastos": [
            {
                "id": g.pk,
                "categoria": g.categoria,
                "categoria_display": g.get_categoria_display(),
                "fecha": g.fecha,
                "monto": monto(g.monto),
                "descripcion": g.descripcion,
                "estado": g.estado,
                "estado_display": g.get_estado_display(),
                "observacion": g.observacion,
                "comprobante": f"/api/gastos/{g.pk}/comprobante/",
            }
            for g in v.gastos.all()
        ],
        "liquidacion": {
            "total_gastos": monto(liquidacion.total_gastos),
            "total_anticipo": monto(liquidacion.total_anticipo),
            "saldo": monto(liquidacion.saldo),
            "resultado": liquidacion.resultado,
            "resultado_display": liquidacion.get_resultado_display(),
            "liquidado_por": str(liquidacion.liquidado_por),
            "liquidada_en": liquidacion.liquidada_en,
        } if liquidacion else None,
    }


def detalle_qs(usuario):
    return viaticos_visibles(usuario).select_related("autorizado_por", "liquidacion__liquidado_por").prefetch_related(
        "gastos"
    )


def responder_detalle(request, pk, status=200):
    return Response(viatico_detalle(detalle_qs(request.user).get(pk=pk)), status=status)


class ViaticosView(APIView):
    """GET: lista (el empleado recibe además su resumen). POST (empleado): solicitar viático."""

    permission_classes = [EmpresaActiva]

    def get(self, request):
        qs = viaticos_visibles(request.user)
        p = request.query_params
        if p.get("estado") in Viatico.Estado.values:
            qs = qs.filter(estado=p["estado"])
        elif p.get("estado") == "POR_LIQUIDAR":
            qs = qs.filter(estado__in=Viatico.ESTADOS_GASTOS)
        if q := p.get("q", "").strip():
            qs = qs.filter(
                Q(concepto__icontains=q) | Q(tarea__titulo__icontains=q)
                | Q(empleado__first_name__icontains=q) | Q(empleado__last_name__icontains=q)
            )
        if request.user.es_administrador and p.get("empleado", "").isdigit():
            qs = qs.filter(empleado=p["empleado"])
        datos = {"resultados": [viatico_resumen(v) for v in qs]}
        if request.user.es_empleado:
            datos["resumen"] = self.resumen(request.user)
        return Response(datos)

    @staticmethod
    def resumen(empleado):
        """Sobre los viáticos abiertos: lo aprobado y el anticipo que aún no cubren los gastos registrados."""
        disponible = por_comprobar = CERO
        abiertos = viaticos_visibles(empleado).filter(estado__in=Viatico.ESTADOS_GASTOS).annotate(
            registrado=Sum("gastos__monto", filter=~Q(gastos__estado=Gasto.Estado.RECHAZADO))
        )
        for v in abiertos:
            registrado = v.registrado or CERO
            disponible += max((v.monto_aprobado or CERO) - registrado, CERO)
            por_comprobar += max(v.anticipo_entregado - registrado, CERO)
        return {"disponible": monto(disponible), "por_comprobar": monto(por_comprobar)}

    def post(self, request):
        if not request.user.es_empleado:
            return Response({"detail": ["Solo los empleados solicitan viáticos."]}, status=403)
        tarea = Tarea.objects.filter(
            pk=request.data.get("tarea") or 0, empresa=request.user.empresa, asignado_a=request.user
        ).first()
        if not tarea:
            return Response({"detail": ["Elija una de sus tareas."]}, status=400)
        concepto = str(request.data.get("concepto", "")).strip()
        if not concepto:
            return Response({"detail": ["Indique el concepto del viático."]}, status=400)
        valor = decimal(request.data.get("monto_solicitado"))
        if valor is None:
            return Response({"detail": ["Indique un monto válido."]}, status=400)
        viatico = Viatico.solicitar(tarea, request.user, concepto[:255], valor)
        return responder_detalle(request, viatico.pk, status=201)


class OpcionesView(APIView):
    """Tareas abiertas del empleado (para solicitar) y categorías de gasto."""

    permission_classes = [EsEmpleado]

    def get(self, request):
        tareas = (
            Tarea.objects.filter(empresa=request.user.empresa, asignado_a=request.user)
            .exclude(estado__in=[Tarea.Estado.COMPLETADA, Tarea.Estado.CANCELADA])
            .order_by("-creada_en")
        )
        return Response({
            "tareas": [tarea_corta(t) for t in tareas],
            "categorias": [{"valor": v, "etiqueta": e} for v, e in Gasto.Categoria.choices],
        })


class ViaticoDetalleView(APIView):
    permission_classes = [EmpresaActiva]

    def get(self, request, pk):
        return Response(viatico_detalle(get_object_or_404(detalle_qs(request.user), pk=pk)))


class AccionView(APIView):
    """Autorizar, rechazar, entregar anticipo y liquidar: la lógica está en los métodos del modelo."""

    permission_classes = [EsAdministrador]
    accion = None

    def post(self, request, pk):
        viatico = get_object_or_404(viaticos_visibles(request.user), pk=pk)
        d = request.data
        if self.accion == "autorizar":
            aprobado = decimal(d.get("monto_aprobado"))
            anticipo = decimal(d.get("anticipo"), opcional=True)
            if aprobado is None or anticipo is None:
                return Response({"detail": ["Indique montos válidos."]}, status=400)
            viatico.autorizar(request.user, aprobado, anticipo)
        elif self.accion == "rechazar":
            viatico.rechazar(request.user, d.get("observacion", ""))
        elif self.accion == "anticipo":
            anticipo = decimal(d.get("anticipo"))
            if anticipo is None:
                return Response({"detail": ["Indique un monto válido."]}, status=400)
            viatico.entregar_anticipo(request.user, anticipo)
        elif self.accion == "liquidar":
            viatico.liquidar(request.user)
        return responder_detalle(request, pk)


class GastosView(APIView):
    """POST (empleado): registrar un gasto con su comprobante."""

    permission_classes = [EsEmpleado]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        viatico = get_object_or_404(viaticos_visibles(request.user), pk=pk)
        form = GastoForm(request.data, request.FILES)
        if not form.is_valid():
            return Response({"detail": [m for errores in form.errors.values() for m in errores]}, status=400)
        d = form.cleaned_data
        viatico.registrar_gasto(request.user, d["comprobante"], d["categoria"], d["fecha"], d["monto"], d["descripcion"])
        return responder_detalle(request, pk, status=201)


class RevisarGastoView(APIView):
    """Aprobar o rechazar un gasto (regla 3: rechazar exige observación)."""

    permission_classes = [EsAdministrador]
    aprobar = True

    def post(self, request, pk):
        gasto = get_object_or_404(Gasto.objects.filter(viatico__tarea__empresa=request.user.empresa), pk=pk)
        observacion = request.data.get("observacion", "")
        if self.aprobar:
            gasto.aprobar(request.user, observacion)
        else:
            gasto.rechazar(request.user, observacion)
        return responder_detalle(request, gasto.viatico_id)


class ComprobanteView(APIView):
    """Sirve el comprobante solo a quien puede verlo (regla 5)."""

    permission_classes = [EmpresaActiva]

    def get(self, request, pk):
        gastos = filtrar_por_usuario(Gasto.objects.all(), request.user, "viatico__tarea__empresa", "viatico__empleado")
        return servir_archivo(get_object_or_404(gastos, pk=pk).comprobante)
