from django.contrib import admin

from .models import Historial, Notificacion


@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("fecha", "empresa", "usuario", "entidad", "entidad_id", "accion")
    list_filter = ("empresa", "entidad")
    search_fields = ("accion", "detalle")

    # Bitácora de solo lectura
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("creada_en", "usuario", "mensaje", "leida")
    list_filter = ("leida",)
