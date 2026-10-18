from django.urls import path

from . import api

urlpatterns = [
    path("viaticos/", api.ViaticosView.as_view(), name="api_viaticos"),
    path("viaticos/opciones/", api.OpcionesView.as_view(), name="api_viaticos_opciones"),
    path("viaticos/<int:pk>/", api.ViaticoDetalleView.as_view(), name="api_viatico"),
    path("viaticos/<int:pk>/autorizar/", api.AccionView.as_view(accion="autorizar"), name="api_viatico_autorizar"),
    path("viaticos/<int:pk>/rechazar/", api.AccionView.as_view(accion="rechazar"), name="api_viatico_rechazar"),
    path("viaticos/<int:pk>/anticipo/", api.AccionView.as_view(accion="anticipo"), name="api_viatico_anticipo"),
    path("viaticos/<int:pk>/liquidar/", api.AccionView.as_view(accion="liquidar"), name="api_viatico_liquidar"),
    path("viaticos/<int:pk>/gastos/", api.GastosView.as_view(), name="api_gastos"),
    path("gastos/<int:pk>/aprobar/", api.RevisarGastoView.as_view(aprobar=True), name="api_gasto_aprobar"),
    path("gastos/<int:pk>/rechazar/", api.RevisarGastoView.as_view(aprobar=False), name="api_gasto_rechazar"),
    path("gastos/<int:pk>/comprobante/", api.ComprobanteView.as_view(), name="api_comprobante"),
]
