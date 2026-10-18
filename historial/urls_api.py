from django.urls import path

from . import api

urlpatterns = [
    path("notificaciones/", api.NotificacionesView.as_view(), name="api_notificaciones"),
    path("notificaciones/<int:pk>/leer/", api.LeerNotificacionView.as_view(), name="api_leer_notificacion"),
    path("notificaciones/leer-todas/", api.LeerTodasView.as_view(), name="api_leer_todas"),
    path("historial/", api.HistorialView.as_view(), name="api_historial"),
]
