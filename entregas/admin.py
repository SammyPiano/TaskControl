from django.contrib import admin

from .models import Entrega, Evidencia, Revision


class SoloLecturaInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EvidenciaInline(SoloLecturaInline):
    model = Evidencia


class RevisionInline(SoloLecturaInline):
    model = Revision


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    """Regla 4: versiones y evidencias no se modifican ni se borran."""

    list_display = ("tarea", "version", "empleado", "estado", "presentada_en")
    list_filter = ("estado", "tarea__empresa")
    search_fields = ("tarea__titulo",)
    inlines = [EvidenciaInline, RevisionInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
