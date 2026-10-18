from django.urls import path

from . import api

urlpatterns = [
    path("tareas/", api.TareasView.as_view(), name="api_tareas"),
    path("tareas/opciones/", api.OpcionesView.as_view(), name="api_tareas_opciones"),
    path("tareas/<int:pk>/", api.TareaDetalleView.as_view(), name="api_tarea"),
    path("tareas/<int:pk>/iniciar/", api.IniciarView.as_view(), name="api_tarea_iniciar"),
    path("mis-tareas/", api.MisTareasView.as_view(), name="api_mis_tareas"),
    path("items/<int:pk>/marcar/", api.MarcarItemView.as_view(), name="api_marcar_item"),
]
