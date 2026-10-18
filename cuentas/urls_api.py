from django.urls import path

from . import api

urlpatterns = [
    path("sesion/", api.SesionView.as_view(), name="api_sesion"),
    path("perfil/", api.PerfilView.as_view(), name="api_perfil"),
    path("usuarios/", api.UsuariosView.as_view(), name="api_usuarios"),
    path("usuarios/<int:pk>/", api.UsuarioDetalleView.as_view(), name="api_usuario"),
]
