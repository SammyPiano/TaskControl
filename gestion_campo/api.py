"""Piezas comunes de la API (DRF): permisos por rol/empresa y errores del modelo como 400."""

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework import exceptions, permissions
from rest_framework.pagination import PageNumberPagination

from cuentas.models import Usuario


class EmpresaActiva(permissions.IsAuthenticated):
    """Autenticado y con empresa activa (regla 5); `roles` opcional."""

    roles = ()
    message = "No tiene permiso para esta acción."

    def has_permission(self, request, view):
        usuario = request.user
        return (
            super().has_permission(request, view)
            and usuario.tiene_empresa_activa
            and (not self.roles or usuario.rol in self.roles)
        )


class EsAdministrador(EmpresaActiva):
    roles = (Usuario.Rol.ADMINISTRADOR,)


class EsEmpleado(EmpresaActiva):
    roles = (Usuario.Rol.EMPLEADO,)


class Paginacion(PageNumberPagination):
    page_size = 20


def manejar_excepcion(exc, context):
    """Los ValidationError de los métodos del modelo llegan a React como 400 con sus mensajes."""
    from rest_framework.views import exception_handler  # import tardío: views importa estos permisos

    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError({"detail": exc.messages})
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(str(exc) or None)
    return exception_handler(exc, context)


def servir_archivo(archivo):
    """Archivos protegidos (fotos, comprobantes): nunca por /media/ directo."""
    from django.http import FileResponse, Http404

    try:
        return FileResponse(archivo.open("rb"))
    except (FileNotFoundError, ValueError):
        raise Http404("Archivo no encontrado.")


def persona(usuario):
    return {"id": usuario.pk, "nombre": str(usuario), "iniciales": usuario.iniciales} if usuario else None


def monto(valor):
    """Montos como string decimal en JSON (nunca float)."""
    return None if valor is None else f"{valor:.2f}"
