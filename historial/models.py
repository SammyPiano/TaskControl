from django.conf import settings
from django.db import models
from django.utils import timezone

from cuentas.models import Empresa


class Historial(models.Model):
    """Bitácora inmutable de cambios de estado (regla 8). Se agrupa por tarea o viático."""

    class Entidad(models.TextChoices):
        TAREA = "tarea", "Tarea"
        VIATICO = "viatico", "Viático"

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="historial")
    entidad = models.CharField(max_length=20, choices=Entidad.choices)
    entidad_id = models.PositiveBigIntegerField()
    accion = models.CharField("acción", max_length=60)
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "registro de historial"
        verbose_name_plural = "historial"
        indexes = [
            models.Index(fields=["empresa", "fecha"]),
            models.Index(fields=["entidad", "entidad_id"]),
        ]

    def __str__(self):
        return f"{self.get_entidad_display()} #{self.entidad_id} · {self.accion}"

    @property
    def enlace(self):
        from .servicios import ruta_spa

        return ruta_spa(self.entidad, self.entidad_id)


class Notificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    mensaje = models.CharField(max_length=255)
    enlace = models.CharField(max_length=255, blank=True)
    leida = models.BooleanField("leída", default=False)
    creada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creada_en", "-id"]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        indexes = [models.Index(fields=["usuario", "leida"])]

    def __str__(self):
        return self.mensaje
