from django.urls import path

from . import api

urlpatterns = [
    path("panel/", api.PanelView.as_view(), name="api_panel"),
    path("reportes/<slug:tipo>/", api.ReporteView.as_view(), name="api_reporte"),
]
