from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion_campo.api import EsAdministrador

from .models import ItemPlantilla, PlantillaChecklist, TipoServicio, guardar_plantilla


def tipos_de(empresa):
    activas = PlantillaChecklist.objects.filter(activa=True).prefetch_related(
        Prefetch("items", queryset=ItemPlantilla.objects.order_by("orden", "id"))
    )
    return (
        TipoServicio.objects.filter(empresa=empresa, activo=True)
        .annotate(usos=Count("tareas", distinct=True))
        .prefetch_related(Prefetch("plantillas", queryset=activas, to_attr="activas"))
    )


def tipo_json(tipo):
    plantilla = tipo.activas[0] if tipo.activas else None
    return {
        "id": tipo.pk,
        "nombre": tipo.nombre,
        "usos": tipo.usos,
        "plantilla": {
            "id": plantilla.pk,
            "nombre": plantilla.nombre,
            "items": [{"id": i.pk, "descripcion": i.descripcion, "obligatorio": i.obligatorio} for i in plantilla.items.all()],
        } if plantilla else None,
    }


def validar_nombre(empresa, nombre, excluir=None):
    nombre = (nombre or "").strip()
    if not nombre:
        return None, "Indique el nombre del servicio."
    if TipoServicio.objects.filter(empresa=empresa, nombre__iexact=nombre).exclude(pk=excluir).exists():
        return None, "Ya existe un tipo de servicio con ese nombre."
    return nombre[:100], None


class TiposView(APIView):
    permission_classes = [EsAdministrador]

    def get(self, request):
        return Response([tipo_json(t) for t in tipos_de(request.user.empresa)])

    def post(self, request):
        archivado = TipoServicio.objects.filter(
            empresa=request.user.empresa, activo=False, nombre__iexact=(request.data.get("nombre") or "").strip()
        ).first()
        if archivado:  # el nombre es único por empresa: se reactiva el servicio archivado con su plantilla
            archivado.activo = True
            archivado.save(update_fields=["activo"])
            return Response(tipo_json(tipos_de(request.user.empresa).get(pk=archivado.pk)), status=201)
        nombre, error = validar_nombre(request.user.empresa, request.data.get("nombre"))
        if error:
            return Response({"detail": [error]}, status=400)
        tipo = TipoServicio.objects.create(empresa=request.user.empresa, nombre=nombre)
        return Response(tipo_json(tipos_de(request.user.empresa).get(pk=tipo.pk)), status=201)


class TipoDetalleView(APIView):
    permission_classes = [EsAdministrador]

    def patch(self, request, pk):
        tipo = get_object_or_404(TipoServicio, pk=pk, empresa=request.user.empresa, activo=True)
        nombre, error = validar_nombre(request.user.empresa, request.data.get("nombre"), excluir=pk)
        if error:
            return Response({"detail": [error]}, status=400)
        tipo.nombre = nombre
        tipo.save(update_fields=["nombre"])
        return Response(tipo_json(tipos_de(request.user.empresa).get(pk=pk)))

    def delete(self, request, pk):
        tipo = get_object_or_404(TipoServicio, pk=pk, empresa=request.user.empresa, activo=True)
        return Response({"archivado": tipo.eliminar()})


class PlantillaView(APIView):
    """PUT: guarda la lista de ítems de la plantilla del tipo de servicio."""

    permission_classes = [EsAdministrador]

    def put(self, request, pk):
        tipo = get_object_or_404(TipoServicio, pk=pk, empresa=request.user.empresa, activo=True)
        items = request.data.get("items")
        if not isinstance(items, list):
            return Response({"detail": ["Envíe la lista de ítems."]}, status=400)
        guardar_plantilla(tipo, items)
        return Response(tipo_json(tipos_de(request.user.empresa).get(pk=pk)))
