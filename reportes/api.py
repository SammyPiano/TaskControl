from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.http import Http404
from django.utils import formats, timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from entregas.models import Entrega
from gestion_campo.api import EsAdministrador
from tareas.models import Tarea
from tareas.api import empleados_de
from viaticos.models import Gasto, Liquidacion, Viatico

from . import servicios
from .exportar import respuesta_csv
from .forms import FiltroReporteForm, PeriodoMixin


def _monto(valor):
    return f"{valor or 0:.2f}"


class PanelView(APIView):
    """Indicadores del panel del administrador, siempre de su empresa (regla 5)."""

    permission_classes = [EsAdministrador]

    def get(self, request):
        empresa = request.user.empresa
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)
        tareas = Tarea.objects.filter(empresa=empresa)

        abiertas = tareas.filter(estado__in=Tarea.ESTADOS_ABIERTOS)
        conteo = abiertas.aggregate(
            total=Count("id"),
            vencidas=Count("id", filter=Q(fecha_limite__lt=hoy)),
        )
        revision = tareas.filter(estado=Tarea.Estado.EN_REVISION).aggregate(
            total=Count("id"), urgentes=Count("id", filter=Q(prioridad=Tarea.Prioridad.URGENTE))
        )
        creadas_hoy = PeriodoMixin.filtrar_periodo(abiertas, "creada_en", hoy, hoy).count()

        cumplimiento = servicios.cumplimiento(empresa, inicio_mes, hoy)
        total = cumplimiento.total
        por_liquidar = Viatico.objects.filter(tarea__empresa=empresa, estado__in=Viatico.ESTADOS_GASTOS).aggregate(
            total=Count("id"), monto=Sum("monto_aprobado")
        )
        gasto_mes = Gasto.objects.filter(
            viatico__tarea__empresa=empresa, estado=Gasto.Estado.APROBADO, fecha__gte=inicio_mes, fecha__lte=hoy
        ).aggregate(total=Count("id"), monto=Sum("monto"))

        en_revision = (
            Entrega.objects.filter(tarea__empresa=empresa, estado=Entrega.Estado.EN_REVISION)
            .select_related("tarea", "empleado")
            .annotate(fotos=Count("evidencias"))
            .order_by("-presentada_en")[:5]
        )

        return Response({
            "fecha": formats.date_format(hoy, "l, j \\d\\e F \\d\\e Y"),
            "mes": formats.date_format(hoy, "F Y"),
            "kpis": {
                "pendientes": conteo["total"],
                "creadas_hoy": creadas_hoy,
                "en_revision": revision["total"],
                "urgentes_en_revision": revision["urgentes"],
                "vencidas": conteo["vencidas"],
                "cumplimiento": round(total[8]) if total and total[8] is not None else None,
                "viaticos_por_liquidar": por_liquidar["total"],
                "monto_por_liquidar": _monto(por_liquidar["monto"]),
                "gasto_mes": _monto(gasto_mes["monto"]),
                "gastos_mes": gasto_mes["total"],
            },
            # Empleado, % cumplimiento (completadas / asignadas del mes)
            "cumplimiento_empleados": [
                {"empleado": fila[0], "porcentaje": round(fila[8] or 0)} for fila in cumplimiento.filas
            ],
            "revisiones": [
                {
                    "id": e.pk,
                    "tarea_id": e.tarea_id,
                    "titulo": e.tarea.titulo,
                    "ubicacion": e.tarea.ubicacion,
                    "empleado": str(e.empleado),
                    "iniciales": e.empleado.iniciales,
                    "version": e.version,
                    "fotos": e.fotos,
                    "presentada_en": e.presentada_en,
                    "urgente": e.tarea.prioridad == Tarea.Prioridad.URGENTE,
                }
                for e in en_revision
            ],
        })


def tramos(desde, hasta, maximo=8):
    """Divide el período en hasta `maximo` tramos de al menos una semana."""
    dias = (hasta - desde).days + 1
    largo = max(7, -(-dias // maximo))
    inicio = desde
    while inicio <= hasta:
        fin = min(inicio + timedelta(days=largo - 1), hasta)
        yield inicio, fin
        inicio = fin + timedelta(days=1)


def serie(tipo, empresa, desde, hasta, empleado):
    """Dos valores por tramo para el gráfico: [principal, comparación]."""
    tareas = Tarea.objects.filter(empresa=empresa).exclude(estado=Tarea.Estado.CANCELADA)
    viaticos = Viatico.objects.filter(tarea__empresa=empresa)
    if empleado:
        tareas, viaticos = tareas.filter(asignado_a=empleado), viaticos.filter(empleado=empleado)
    filas = []
    for n, (inicio, fin) in enumerate(tramos(desde, hasta), start=1):
        etiqueta = f"Sem. {n}" if (fin - inicio).days < 7 else formats.date_format(inicio, "d/m")
        if tipo == "viaticos":
            del_tramo = PeriodoMixin.filtrar_periodo(viaticos, "solicitado_en", inicio, fin)
            a = _monto(del_tramo.aggregate(s=Sum("monto_aprobado"))["s"])
            b = _monto(Gasto.objects.filter(viatico__in=del_tramo, estado=Gasto.Estado.APROBADO).aggregate(s=Sum("monto"))["s"])
        else:
            t = PeriodoMixin.filtrar_periodo(tareas, "creada_en", inicio, fin).aggregate(
                total=Count("id"),
                completadas=Count("id", filter=Q(estado=Tarea.Estado.COMPLETADA)),
                abiertas=Count("id", filter=~Q(estado=Tarea.Estado.COMPLETADA)),
            )
            a, b = (t["completadas"], t["total"]) if tipo == "cumplimiento" else (t["abiertas"], t["total"])
        filas.append({"etiqueta": etiqueta, "desde": inicio, "hasta": fin, "a": a, "b": b})
    return filas


LEYENDAS = {
    "cumplimiento": ["Completadas", "Asignadas"],
    "pendientes": ["Sin completar", "Creadas"],
    "viaticos": ["Aprobado", "Gastos aprobados"],
}


class ReporteView(APIView):
    """Reporte `tipo` del período (regla 5: solo la empresa del administrador). ?formato=csv lo exporta."""

    permission_classes = [EsAdministrador]

    def get(self, request, tipo):
        if tipo not in servicios.REPORTES:
            raise Http404
        empresa = request.user.empresa
        form = FiltroReporteForm(request.query_params, empresa=empresa)
        if not form.is_valid():
            return Response({"detail": [m for errores in form.errors.values() for m in errores]}, status=400)
        d = form.cleaned_data
        reporte = servicios.REPORTES[tipo][1](empresa, **d)

        if request.query_params.get("formato") == "csv":
            nombre = f"reporte_{tipo}_{d['desde']:%Y%m%d}_{d['hasta']:%Y%m%d}"
            return respuesta_csv(nombre, reporte.encabezados, reporte.filas_csv())

        cumplimiento = reporte if tipo == "cumplimiento" else servicios.cumplimiento(empresa, **d)
        total = cumplimiento.total
        liquidaciones = Liquidacion.objects.filter(viatico__tarea__empresa=empresa)
        if d["empleado"]:
            liquidaciones = liquidaciones.filter(viatico__empleado=d["empleado"])
        liquidado = PeriodoMixin.filtrar_periodo(liquidaciones, "liquidada_en", d["desde"], d["hasta"]).aggregate(
            s=Sum("total_gastos")
        )["s"]

        return Response({
            "tipo": tipo,
            "titulo": reporte.titulo,
            "descripcion": reporte.descripcion,
            "desde": d["desde"],
            "hasta": d["hasta"],
            "columnas": [{"titulo": c, "numero": t not in (servicios.TEXTO, servicios.FECHA)} for c, t in reporte.columnas],
            "filas": [[c["texto"] for c in fila] for fila in reporte.tabla()],
            "total": [c["texto"] for c in reporte.tabla_total()] if reporte.total else None,
            "resumen": {
                "cumplimiento": round(total[8]) if total and total[8] is not None else None,
                "completadas": total[2] if total else 0,
                "retrasadas": (total[4] + total[6]) if total else 0,
                "viaticos_liquidados": _monto(liquidado),
            },
            "leyenda": LEYENDAS[tipo],
            "serie": serie(tipo, empresa, d["desde"], d["hasta"], d["empleado"]),
            "pestanas": [{"tipo": t, "nombre": nombre} for t, (nombre, _) in servicios.REPORTES.items()],
            "empleados": [{"id": u.pk, "nombre": str(u)} for u in empleados_de(empresa)],
        })
