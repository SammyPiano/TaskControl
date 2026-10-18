from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from .views import spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include([
        path("", include("cuentas.urls_api")),
        path("", include("configuracion.urls_api")),
        path("", include("tareas.urls_api")),
        path("", include("entregas.urls_api")),
        path("", include("viaticos.urls_api")),
        path("", include("historial.urls_api")),
        path("", include("reportes.urls_api")),
    ])),
    re_path(r"^app(?:/.*)?$", spa, name="spa"),
    path("", RedirectView.as_view(url="/app/", permanent=False)),
]
# Sin /media/ público: fotos y comprobantes solo por los endpoints protegidos de la API.
