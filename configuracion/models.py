from django.db import models

from cuentas.models import Empresa


class TipoServicio(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="tipos_servicio")
    nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="tiposervicio_unico_por_empresa"),
        ]

    def __str__(self):
        return self.nombre


class PlantillaChecklist(models.Model):
    tipo_servicio = models.ForeignKey(
        TipoServicio, on_delete=models.CASCADE, related_name="plantillas", verbose_name="tipo de servicio"
    )
    nombre = models.CharField(max_length=150)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo_servicio__nombre", "nombre"]
        verbose_name = "plantilla de checklist"
        verbose_name_plural = "plantillas de checklist"

    def __str__(self):
        return f"{self.nombre} ({self.tipo_servicio})"


class ItemPlantilla(models.Model):
    plantilla = models.ForeignKey(PlantillaChecklist, on_delete=models.CASCADE, related_name="items")
    descripcion = models.CharField("descripción", max_length=255)
    orden = models.PositiveIntegerField(default=0)
    obligatorio = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "ítem de plantilla"
        verbose_name_plural = "ítems de plantilla"

    def __str__(self):
        return self.descripcion


def guardar_plantilla(tipo_servicio, items):
    """Reemplaza los ítems de la plantilla activa del tipo (la crea si no existe). Las tareas ya creadas no cambian."""
    from django.core.exceptions import ValidationError
    from django.db import transaction

    limpios = [(str(i.get("descripcion", "")).strip()[:255], bool(i.get("obligatorio", True))) for i in items]
    limpios = [i for i in limpios if i[0]]
    if not limpios:
        raise ValidationError("La plantilla necesita al menos un ítem.")
    with transaction.atomic():
        plantilla = tipo_servicio.plantillas.filter(activa=True).first() or PlantillaChecklist.objects.create(
            tipo_servicio=tipo_servicio, nombre=tipo_servicio.nombre
        )
        plantilla.items.all().delete()
        ItemPlantilla.objects.bulk_create(
            ItemPlantilla(plantilla=plantilla, descripcion=d, obligatorio=o, orden=n)
            for n, (d, o) in enumerate(limpios, start=1)
        )
    return plantilla
