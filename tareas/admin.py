from django.contrib import admin

from .models import ItemChecklist, Tarea


class ItemChecklistInline(admin.TabularInline):
    model = ItemChecklist
    extra = 0


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "empresa", "asignado_a", "estado", "prioridad", "fecha_limite")
    list_filter = ("empresa", "estado", "prioridad")
    search_fields = ("titulo", "ubicacion")
    inlines = [ItemChecklistInline]
