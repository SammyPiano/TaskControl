from django.contrib import admin

from .models import Gasto, Liquidacion, Viatico


class GastoInline(admin.TabularInline):
    model = Gasto
    extra = 0
    can_delete = False
    readonly_fields = ("categoria", "fecha", "monto", "descripcion", "comprobante", "estado", "observacion",
                       "revisado_por", "revisado_en")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Viatico)
class ViaticoAdmin(admin.ModelAdmin):
    """Los cambios de estado se hacen desde la aplicación (métodos del modelo)."""

    list_display = ("concepto", "tarea", "empleado", "estado", "monto_solicitado", "monto_aprobado", "anticipo_entregado")
    list_filter = ("estado", "tarea__empresa")
    search_fields = ("concepto", "tarea__titulo")
    inlines = [GastoInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Liquidacion)
class LiquidacionAdmin(admin.ModelAdmin):
    list_display = ("viatico", "total_gastos", "total_anticipo", "saldo", "resultado", "liquidada_en")
    list_filter = ("resultado",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
