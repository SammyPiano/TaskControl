from django.urls import path

from . import api

urlpatterns = [
    path("entregas/", api.RevisionesView.as_view(), name="api_entregas"),
    path("entregas/<int:pk>/", api.EntregaDetalleView.as_view(), name="api_entrega"),
    path("entregas/<int:pk>/aprobar/", api.AprobarView.as_view(), name="api_entrega_aprobar"),
    path("entregas/<int:pk>/devolver/", api.DevolverView.as_view(), name="api_entrega_devolver"),
    path("tareas/<int:pk>/entregas/", api.PresentarView.as_view(), name="api_presentar"),
    path("evidencias/<int:pk>/archivo/", api.EvidenciaArchivoView.as_view(), name="api_evidencia"),
]
