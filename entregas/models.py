from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone

from gestion_campo.imagenes import validar_tamano
from historial.servicios import cambio, notificar, notificar_administradores, registrar
from tareas.models import Tarea


class Entrega(models.Model):
    class Estado(models.TextChoices):
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADA = "APROBADA", "Aprobada"
        DEVUELTA = "DEVUELTA", "Devuelta"

    COLOR_ESTADO = {
        Estado.EN_REVISION: "info",
        Estado.APROBADA: "success",
        Estado.DEVUELTA: "warning",
    }

    # Versiones y evidencias nunca se borran (PROTECT)
    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name="entregas")
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entregas")
    version = models.PositiveIntegerField("versión")
    comentario = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.EN_REVISION)
    presentada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-version"]
        verbose_name = "entrega"
        verbose_name_plural = "entregas"
        constraints = [models.UniqueConstraint(fields=["tarea", "version"], name="entrega_version_unica")]
        indexes = [models.Index(fields=["estado", "presentada_en"])]

    def __str__(self):
        return f"{self.tarea} · v{self.version}"

    @property
    def color_estado(self):
        return self.COLOR_ESTADO.get(self.estado, "secondary")

    @classmethod
    def presentar(cls, tarea, empleado, evidencias, comentario=""):
        """Solicita revisión (regla 2). `evidencias`: lista de (archivo, descripción)."""
        with transaction.atomic():
            tarea = Tarea.objects.select_for_update().get(pk=tarea.pk)
            if empleado.pk != tarea.asignado_a_id:
                raise ValidationError("Solo el empleado asignado puede entregar la tarea.")
            if not tarea.esta_abierta:
                raise ValidationError("La tarea no admite entregas en su estado actual.")
            pendientes = tarea.obligatorios_pendientes()
            if pendientes:
                raise ValidationError(
                    "Complete los ítems obligatorios del checklist: "
                    + ", ".join(i.descripcion for i in pendientes) + "."
                )
            if not evidencias:
                raise ValidationError("Agregue al menos una foto como evidencia.")

            ultima = tarea.entregas.aggregate(m=Max("version"))["m"] or 0
            entrega = cls.objects.create(tarea=tarea, empleado=empleado, version=ultima + 1, comentario=comentario)
            for archivo, descripcion in evidencias:
                Evidencia.objects.create(entrega=entrega, archivo=archivo, descripcion=descripcion)

            anterior = tarea.estado
            tarea.estado = Tarea.Estado.EN_REVISION
            tarea.save(update_fields=["estado", "actualizada_en"])
            registrar(empleado, tarea, "Entrega presentada", f"Versión {entrega.version}. {cambio(tarea, anterior)}")
            notificar_administradores(
                tarea.empresa_id, f"{empleado} entregó «{tarea}» (v{entrega.version}) para revisión.",
                "entrega", entrega.pk,
            )
        return entrega

    def aprobar(self, revisor, observaciones=""):
        """Regla 1: solo la aprobación de un administrador completa la tarea."""
        return self._revisar(revisor, Revision.Decision.APROBADA, observaciones)

    def devolver(self, revisor, observaciones):
        """Reglas 3 y 4: exige observación; el empleado presentará una nueva versión."""
        if not (observaciones or "").strip():
            raise ValidationError("Indique la observación para devolver la entrega.")
        return self._revisar(revisor, Revision.Decision.DEVUELTA, observaciones)

    def _revisar(self, revisor, decision, observaciones):
        with transaction.atomic():
            tarea = Tarea.objects.select_for_update().get(pk=self.tarea_id)
            estado_actual = Entrega.objects.select_for_update().values_list("estado", flat=True).get(pk=self.pk)
            if estado_actual != self.Estado.EN_REVISION:
                raise ValidationError("Esta entrega ya fue revisada.")
            if not revisor.es_administrador or revisor.empresa_id != tarea.empresa_id:
                raise ValidationError("Solo un administrador de la empresa puede revisar la entrega.")

            revision = Revision.objects.create(
                entrega=self, revisor=revisor, decision=decision, observaciones=(observaciones or "").strip()
            )
            self.estado = decision
            self.save(update_fields=["estado"])

            anterior = tarea.estado
            if decision == Revision.Decision.APROBADA:
                tarea.estado = Tarea.Estado.COMPLETADA
                tarea.completada_en = timezone.now()
                aviso = f"Su entrega de «{tarea}» fue aprobada."
            else:
                tarea.estado = Tarea.Estado.DEVUELTA
                aviso = f"Su entrega de «{tarea}» fue devuelta: {revision.observaciones}"
            tarea.save(update_fields=["estado", "completada_en", "actualizada_en"])
            detalle = f"Versión {self.version}. {cambio(tarea, anterior)}"
            if revision.observaciones:
                detalle += f". Observaciones: {revision.observaciones}"
            registrar(revisor, tarea, f"Entrega {revision.get_decision_display().lower()}", detalle)
            notificar(tarea.asignado_a, aviso, "tarea", tarea.pk)
            self.tarea = tarea
        return revision


def ruta_evidencia(instancia, nombre):
    return f"evidencias/{timezone.localdate():%Y/%m}/{nombre}"


class Evidencia(models.Model):
    entrega = models.ForeignKey(Entrega, on_delete=models.PROTECT, related_name="evidencias")
    archivo = models.ImageField(upload_to=ruta_evidencia, validators=[validar_tamano])
    descripcion = models.CharField("descripción", max_length=255, blank=True)
    subida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "evidencia"
        verbose_name_plural = "evidencias"

    def __str__(self):
        return self.descripcion or self.archivo.name


class Revision(models.Model):
    class Decision(models.TextChoices):
        APROBADA = Entrega.Estado.APROBADA.value, "Aprobada"
        DEVUELTA = Entrega.Estado.DEVUELTA.value, "Devuelta"

    entrega = models.OneToOneField(Entrega, on_delete=models.PROTECT, related_name="revision")
    revisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="revisiones")
    decision = models.CharField("decisión", max_length=12, choices=Decision.choices)
    observaciones = models.TextField(blank=True)
    revisada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "revisión"
        verbose_name_plural = "revisiones"

    def __str__(self):
        return f"{self.entrega} · {self.get_decision_display()}"
