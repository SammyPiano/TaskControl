from django.contrib import admin

from .models import ItemPlantilla, PlantillaChecklist, TipoServicio


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa")
    list_filter = ("empresa",)
    search_fields = ("nombre",)


class ItemPlantillaInline(admin.TabularInline):
    model = ItemPlantilla
    extra = 1


@admin.register(PlantillaChecklist)
class PlantillaChecklistAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo_servicio", "activa")
    list_filter = ("activa", "tipo_servicio__empresa")
    inlines = [ItemPlantillaInline]
