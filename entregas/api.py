from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.mixins import filtrar_por_usuario
from gestion_campo.api import EmpresaActiva, EsAdministrador, EsEmpleado, persona, servir_archivo
from tareas.api import detalle_qs, entrega_json, tarea_detalle, tareas_visibles

from .forms import EntregaForm
from .models import Entrega, Evidencia


def entregas_empresa(usuario):
    return Entrega.objects.filter(tarea__empresa=usuario.empresa_id)


def evidencia_json(ev):
    return {"id": ev.pk, "descripcion": ev.descripcion, "url": f"/api/evidencias/{ev.pk}/archivo/"}


class RevisionesView(APIView):
    """Bandeja de entregas en revisión de la empresa, de la más antigua a la más reciente."""

    permission_classes = [EsAdministrador]

    def get(self, request):
        qs = (
            entregas_empresa(request.user).filter(estado=Entrega.Estado.EN_REVISION)
            .select_related("tarea__tipo_servicio", "empleado")
            .annotate(num_fotos=Count("evidencias"))
            .order_by("presentada_en", "pk")
        )
        return Response([
            {
                "id": e.pk,
                "version": e.version,
                "presentada_en": e.presentada_en,
                "fotos": e.num_fotos,
                "empleado": persona(e.empleado),
                "tarea": {
                    "id": e.tarea_id,
                    "codigo": e.tarea.codigo,
                    "titulo": e.tarea.titulo,
                    "ubicacion": e.tarea.ubicacion,
                    "prioridad": e.tarea.prioridad,
                    "prioridad_display": e.tarea.get_prioridad_display(),
                },
            }
            for e in qs
        ])


class EntregaDetalleView(APIView):
    permission_classes = [EsAdministrador]

    def get(self, request, pk):
        entrega = get_object_or_404(
            entregas_empresa(request.user)
            .select_related("empleado", "revision__revisor")
            .prefetch_related("evidencias"),
            pk=pk,
        )
        tarea = detalle_qs(request.user).get(pk=entrega.tarea_id)
        return Response({
            **entrega_json(entrega),
            "empleado": persona(entrega.empleado),
            "evidencias": [evidencia_json(ev) for ev in entrega.evidencias.all()],
            "tarea": tarea_detalle(tarea),
        })


class AprobarView(APIView):
    """Regla 1: la aprobación del administrador completa la tarea."""

    permission_classes = [EsAdministrador]

    def post(self, request, pk):
        entrega = get_object_or_404(entregas_empresa(request.user), pk=pk)
        entrega.aprobar(request.user, request.data.get("observaciones", ""))
        return Response({"estado": Entrega.Estado.APROBADA})


class DevolverView(APIView):
    """Reglas 3 y 4: exige observación; el empleado presentará una nueva versión."""

    permission_classes = [EsAdministrador]

    def post(self, request, pk):
        entrega = get_object_or_404(entregas_empresa(request.user), pk=pk)
        entrega.devolver(request.user, request.data.get("observaciones", ""))
        return Response({"estado": Entrega.Estado.DEVUELTA})


class PresentarView(APIView):
    """Regla 2: ítems obligatorios marcados y al menos una foto (lo valida Entrega.presentar)."""

    permission_classes = [EsEmpleado]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
        form = EntregaForm(request.data, request.FILES)
        if not form.is_valid():
            return Response({"detail": [m for errores in form.errors.values() for m in errores]}, status=400)
        Entrega.presentar(tarea, request.user, form.cleaned_data["fotos"], form.cleaned_data["comentario"])
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=pk)), status=201)


class EvidenciaArchivoView(APIView):
    """Sirve la foto solo a quien puede verla (regla 5)."""

    permission_classes = [EmpresaActiva]

    def get(self, request, pk):
        evidencias = filtrar_por_usuario(
            Evidencia.objects.all(), request.user, "entrega__tarea__empresa", "entrega__empleado"
        )
        return servir_archivo(get_object_or_404(evidencias, pk=pk).archivo)
