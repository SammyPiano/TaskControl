from datetime import date

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion_campo.api import EmpresaActiva, EsAdministrador, Paginacion, persona
from reportes.exportar import respuesta_csv
from reportes.forms import PeriodoMixin

from .models import Historial, Notificacion


class PaginacionHistorial(Paginacion):
    page_size = 30


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ["id", "mensaje", "enlace", "leida", "creada_en"]


class NotificacionesView(ListAPIView):
    """Solo las del usuario actual."""

    permission_classes = [EmpresaActiva]
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        return self.request.user.notificaciones.all()


class LeerNotificacionView(APIView):
    permission_classes = [EmpresaActiva]

    def post(self, request, pk):
        notificacion = get_object_or_404(request.user.notificaciones, pk=pk)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        return Response(NotificacionSerializer(notificacion).data)


class LeerTodasView(APIView):
    permission_classes = [EmpresaActiva]

    def post(self, request):
        request.user.notificaciones.filter(leida=False).update(leida=True)
        return Response(status=204)


class HistorialView(ListAPIView):
    """Bitácora de la empresa (solo administradores). ?formato=csv exporta lo filtrado."""

    permission_classes = [EsAdministrador]
    pagination_class = PaginacionHistorial

    def get_queryset(self):
        p = self.request.query_params
        qs = Historial.objects.filter(empresa=self.request.user.empresa).select_related("usuario")
        if q := p.get("q", "").strip():
            filtro = (
                Q(accion__icontains=q) | Q(detalle__icontains=q)
                | Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q)
                | Q(usuario__username__icontains=q)
            )
            if q.upper().removeprefix("TC-").removeprefix("VIA-").isdigit():
                filtro |= Q(entidad_id=int(q.upper().removeprefix("TC-").removeprefix("VIA-")))
            qs = qs.filter(filtro)
        if p.get("entidad") in Historial.Entidad.values:
            qs = qs.filter(entidad=p["entidad"])
            if p.get("entidad_id", "").isdigit():
                qs = qs.filter(entidad_id=p["entidad_id"])
        if p.get("accion"):
            qs = qs.filter(accion=p["accion"])
        if p.get("usuario", "").isdigit():
            qs = qs.filter(usuario=p["usuario"])
        try:
            desde = date.fromisoformat(p["desde"]) if p.get("desde") else None
            hasta = date.fromisoformat(p["hasta"]) if p.get("hasta") else None
        except ValueError:
            raise ValidationError({"detail": ["Fechas inválidas."]})
        return PeriodoMixin.filtrar_periodo(qs, "fecha", desde, hasta)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get("formato") == "csv":
            filas = (
                (timezone.localtime(h.fecha), str(h.usuario), h.get_entidad_display(), h.entidad_id, h.accion, h.detalle)
                for h in qs.iterator()
            )
            return respuesta_csv("historial", ["Fecha", "Usuario", "Entidad", "ID", "Acción", "Detalle"], filas)
        pagina = self.paginate_queryset(qs)
        respuesta = self.get_paginated_response([
            {
                "id": h.pk,
                "usuario": persona(h.usuario),
                "entidad": h.entidad,
                "entidad_display": h.get_entidad_display(),
                "entidad_id": h.entidad_id,
                "accion": h.accion,
                "detalle": h.detalle,
                "fecha": h.fecha,
                "enlace": h.enlace,
            }
            for h in pagina
        ])
        respuesta.data["acciones"] = list(
            Historial.objects.filter(empresa=request.user.empresa).order_by("accion")
            .values_list("accion", flat=True).distinct()
        )
        return respuesta
