from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from configuracion.api import tipo_json, tipos_de
from configuracion.models import TipoServicio
from cuentas.mixins import filtrar_por_usuario
from cuentas.models import Usuario
from gestion_campo.api import EmpresaActiva, EsAdministrador, EsEmpleado, persona

from .models import ItemChecklist, Tarea


def empleados_de(empresa):
    return Usuario.objects.filter(empresa=empresa, rol=Usuario.Rol.EMPLEADO, is_active=True).order_by(
        "first_name", "last_name", "username"
    )


def con_progreso(queryset):
    return queryset.select_related("asignado_a", "tipo_servicio").annotate(
        items_total=Count("items", distinct=True),
        items_hechos=Count("items", filter=Q(items__completado=True), distinct=True),
    )


def progreso(tarea):
    total, hechos = tarea.items_total, tarea.items_hechos
    return {"hechos": hechos, "total": total, "porcentaje": round(hechos * 100 / total) if total else 0}


def tarea_resumen(t):
    return {
        "id": t.pk,
        "codigo": t.codigo,
        "titulo": t.titulo,
        "ubicacion": t.ubicacion,
        "tipo_servicio": t.tipo_servicio.nombre,
        "asignado": persona(t.asignado_a),
        "prioridad": t.prioridad,
        "prioridad_display": t.get_prioridad_display(),
        "estado": t.estado,
        "estado_display": t.get_estado_display(),
        "fecha_limite": t.fecha_limite,
        "vencida": t.vencida,
        "progreso": progreso(t),
    }


def entrega_json(e):
    revision = getattr(e, "revision", None)
    return {
        "id": e.pk,
        "version": e.version,
        "estado": e.estado,
        "estado_display": e.get_estado_display(),
        "comentario": e.comentario,
        "presentada_en": e.presentada_en,
        "fotos": len(e.evidencias.all()),
        "revision": {
            "decision": revision.decision,
            "observaciones": revision.observaciones,
            "revisor": str(revision.revisor),
            "revisada_en": revision.revisada_en,
        } if revision else None,
    }


def tarea_detalle(t):
    return {
        **tarea_resumen(t),
        "tipo_servicio_id": t.tipo_servicio_id,
        "descripcion": t.descripcion,
        "criterios_aceptacion": t.criterios_aceptacion,
        "creado_por": persona(t.creado_por),
        "creada_en": t.creada_en,
        "completada_en": t.completada_en,
        "abierta": t.esta_abierta,
        "items": [
            {"id": i.pk, "descripcion": i.descripcion, "obligatorio": i.obligatorio, "completado": i.completado}
            for i in t.items.all()
        ],
        "entregas": [entrega_json(e) for e in t.entregas.all()],
    }


def tareas_visibles(usuario):
    """Regla 5: el empleado solo las suyas; el administrador, las de su empresa."""
    return filtrar_por_usuario(Tarea.objects.all(), usuario, campo_propietario="asignado_a")


def detalle_qs(usuario):
    from entregas.models import Entrega

    entregas = Entrega.objects.select_related("revision__revisor").prefetch_related("evidencias")
    return con_progreso(tareas_visibles(usuario)).select_related("creado_por").prefetch_related(
        Prefetch("items", queryset=ItemChecklist.objects.order_by("orden", "id")),
        Prefetch("entregas", queryset=entregas),
    )


class TareaSerializer(serializers.ModelSerializer):
    """Datos que el administrador puede editar. Empleado y tipo se limitan a su empresa."""

    items = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)

    class Meta:
        model = Tarea
        fields = [
            "titulo", "descripcion", "tipo_servicio", "prioridad", "ubicacion", "fecha_limite",
            "asignado_a", "criterios_aceptacion", "items",
        ]

    def __init__(self, *args, empresa, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_servicio"].queryset = TipoServicio.objects.filter(empresa=empresa)
        self.fields["asignado_a"].queryset = empleados_de(empresa)
        self.fields["tipo_servicio"].error_messages["does_not_exist"] = "Elija un tipo de servicio válido."
        self.fields["asignado_a"].error_messages["does_not_exist"] = "Elija un empleado activo de su empresa."


class TareasView(ListAPIView):
    """GET (administrador): lista filtrable de las tareas de su empresa. POST: crear y asignar."""

    permission_classes = [EsAdministrador]

    def get_queryset(self):
        p = self.request.query_params
        qs = con_progreso(tareas_visibles(self.request.user)).order_by("-creada_en", "-pk")
        if q := p.get("q", "").strip():
            filtro = Q(titulo__icontains=q) | Q(ubicacion__icontains=q) | Q(descripcion__icontains=q)
            if q.upper().removeprefix("TC-").isdigit():
                filtro |= Q(pk=int(q.upper().removeprefix("TC-")))
            qs = qs.filter(filtro)
        if p.get("estado") in Tarea.Estado.values:
            qs = qs.filter(estado=p["estado"])
        elif p.get("estado") == "VENCIDA":
            from django.utils import timezone

            qs = qs.filter(estado__in=Tarea.ESTADOS_ABIERTOS, fecha_limite__lt=timezone.localdate())
        if p.get("prioridad") in Tarea.Prioridad.values:
            qs = qs.filter(prioridad=p["prioridad"])
        if p.get("empleado", "").isdigit():
            qs = qs.filter(asignado_a=p["empleado"])
        if p.get("desde"):
            qs = qs.filter(fecha_limite__gte=p["desde"])
        if p.get("hasta"):
            qs = qs.filter(fecha_limite__lte=p["hasta"])
        return qs

    def list(self, request, *args, **kwargs):
        pagina = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([tarea_resumen(t) for t in pagina])

    def post(self, request):
        serializer = TareaSerializer(data=request.data, empresa=request.user.empresa)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data.pop("items", [])
        with transaction.atomic():
            tarea = serializer.save(empresa=request.user.empresa, creado_por=request.user)
            tarea.crear_checklist(items)
            tarea.registrar_asignacion(request.user)
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=tarea.pk)), status=201)


class MisTareasView(APIView):
    """Tareas del empleado: abiertas y en revisión, de la fecha límite más próxima a la más lejana."""

    permission_classes = [EsEmpleado]

    def get(self, request):
        qs = (
            con_progreso(tareas_visibles(request.user))
            .filter(estado__in=[*Tarea.ESTADOS_ABIERTOS, Tarea.Estado.EN_REVISION])
            .order_by(F("fecha_limite").asc(nulls_last=True), "-creada_en", "-pk")
        )
        return Response([tarea_resumen(t) for t in qs])


class TareaDetalleView(APIView):
    permission_classes = [EmpresaActiva]

    def get(self, request, pk):
        return Response(tarea_detalle(get_object_or_404(detalle_qs(request.user), pk=pk)))

    def patch(self, request, pk):
        if not request.user.es_administrador:
            return Response({"detail": ["Solo un administrador puede editar la tarea."]}, status=403)
        tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
        if not tarea.esta_abierta:
            return Response({"detail": ["La tarea no admite cambios en su estado actual."]}, status=400)
        serializer = TareaSerializer(tarea, data=request.data, partial=True, empresa=request.user.empresa)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("items", None)
        anterior = tarea.asignado_a_id
        with transaction.atomic():
            tarea = serializer.save()
            if tarea.asignado_a_id != anterior:
                tarea.registrar_asignacion(request.user)
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=pk)))


class IniciarView(APIView):
    """PENDIENTE → EN_PROCESO (lo decide el modelo)."""

    permission_classes = [EsEmpleado]

    def post(self, request, pk):
        tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
        tarea.iniciar()
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=pk)))


class MarcarItemView(APIView):
    permission_classes = [EsEmpleado]

    def post(self, request, pk):
        item = get_object_or_404(
            ItemChecklist.objects.select_related("tarea"),
            pk=pk, tarea__empresa=request.user.empresa, tarea__asignado_a=request.user,
        )
        item.marcar(bool(request.data.get("completado")))
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=item.tarea_id)))


class OpcionesView(APIView):
    """Catálogos para el formulario de tareas y los filtros."""

    permission_classes = [EsAdministrador]

    def get(self, request):
        empresa = request.user.empresa
        return Response({
            "tipos": [tipo_json(t) for t in tipos_de(empresa)],
            "empleados": [persona(u) for u in empleados_de(empresa)],
            "prioridades": [{"valor": v, "etiqueta": e} for v, e in Tarea.Prioridad.choices],
            "estados": [{"valor": v, "etiqueta": e} for v, e in Tarea.Estado.choices],
        })
