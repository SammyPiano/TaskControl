from django.urls import path

from . import api

urlpatterns = [
    path("servicios/", api.TiposView.as_view(), name="api_servicios"),
    path("servicios/<int:pk>/", api.TipoDetalleView.as_view(), name="api_servicio"),
    path("servicios/<int:pk>/plantilla/", api.PlantillaView.as_view(), name="api_plantilla"),
]
