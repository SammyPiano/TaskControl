from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from configuracion.models import TipoServicio
from cuentas.models import Empresa
from historial.servicios import cambio, notificar, registrar


class Tarea(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        EN_REVISION = "EN_REVISION", "En revisión"
        DEVUELTA = "DEVUELTA", "Devuelta"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    # Estados en que el empleado puede trabajar el checklist y el admin editar la tarea
    ESTADOS_ABIERTOS = (Estado.PENDIENTE, Estado.EN_PROCESO, Estado.DEVUELTA)

    COLOR_ESTADO = {
        Estado.PENDIENTE: "secondary",
        Estado.EN_PROCESO: "primary",
        Estado.EN_REVISION: "info",
        Estado.DEVUELTA: "warning",
        Estado.COMPLETADA: "success",
        Estado.CANCELADA: "dark",
    }
    COLOR_PRIORIDAD = {
        Prioridad.BAJA: "light",
        Prioridad.MEDIA: "secondary",
        Prioridad.ALTA: "warning",
        Prioridad.URGENTE: "danger",
    }

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="tareas")
    tipo_servicio = models.ForeignKey(
        TipoServicio, on_delete=models.PROTECT, related_name="tareas", verbose_name="tipo de servicio"
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tareas_asignadas", verbose_name="asignado a"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tareas_creadas"
    )
    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    ubicacion = models.CharField("ubicación", max_length=255, blank=True)
    criterios_aceptacion = models.TextField("criterios de aceptación", blank=True)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    fecha_limite = models.DateField("fecha límite", null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    completada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada_en"]
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["asignado_a", "estado"]),
        ]

    def __str__(self):
        return self.titulo

    @property
    def codigo(self):
        return f"TC-{self.pk:04d}"

    @property
    def esta_abierta(self):
        return self.estado in self.ESTADOS_ABIERTOS

    @property
    def vencida(self):
        return bool(self.fecha_limite) and self.esta_abierta and self.fecha_limite < timezone.localdate()

    @property
    def color_estado(self):
        return self.COLOR_ESTADO.get(self.estado, "secondary")

    @property
    def color_prioridad(self):
        return self.COLOR_PRIORIDAD.get(self.prioridad, "secondary")

    def progreso(self):
        items = list(self.items.all())
        hechos = sum(1 for i in items if i.completado)
        total = len(items)
        return {"hechos": hechos, "total": total, "porcentaje": round(hechos * 100 / total) if total else 0}

    def obligatorios_pendientes(self):
        return list(self.items.filter(obligatorio=True, completado=False))

    @transaction.atomic
    def copiar_plantilla(self, plantilla):
        if plantilla.tipo_servicio_id != self.tipo_servicio_id:
            raise ValidationError("La plantilla no corresponde al tipo de servicio de la tarea.")
        ItemChecklist.objects.bulk_create(
            ItemChecklist(tarea=self, descripcion=i.descripcion, orden=i.orden, obligatorio=i.obligatorio)
            for i in plantilla.items.all()
        )

    @transaction.atomic
    def crear_checklist(self, items):
        """`items`: [{"descripcion", "obligatorio"}] editados desde la plantilla al crear la tarea."""
        ItemChecklist.objects.bulk_create(
            ItemChecklist(tarea=self, descripcion=d, obligatorio=bool(i.get("obligatorio", True)), orden=n)
            for n, (i, d) in enumerate(((i, str(i.get("descripcion", "")).strip()[:255]) for i in items), start=1)
            if d
        )

    def iniciar(self):
        """PENDIENTE → EN_PROCESO al empezar a trabajar."""
        if self.estado == self.Estado.PENDIENTE:
            self.estado = self.Estado.EN_PROCESO
            self.save(update_fields=["estado", "actualizada_en"])
            registrar(self.asignado_a, self, "Iniciada", cambio(self, self.Estado.PENDIENTE))

    def registrar_asignacion(self, admin):
        """Historial y aviso al empleado al crear o reasignar la tarea."""
        registrar(admin, self, "Asignada", f"Asignada a {self.asignado_a}.")
        notificar(self.asignado_a, f"Nueva tarea asignada: «{self.titulo}».", "tarea", self.pk)


class ItemChecklist(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="items")
    descripcion = models.CharField("descripción", max_length=255)
    orden = models.PositiveIntegerField(default=0)
    obligatorio = models.BooleanField(default=True)
    completado = models.BooleanField(default=False)
    marcado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "ítem de checklist"
        verbose_name_plural = "ítems de checklist"

    def __str__(self):
        return self.descripcion

    @transaction.atomic
    def marcar(self, completado):
        if not self.tarea.esta_abierta:
            raise ValidationError("La tarea no admite cambios en el checklist en su estado actual.")
        self.completado = completado
        self.marcado_en = timezone.now() if completado else None
        self.save(update_fields=["completado", "marcado_en"])
        if completado:
            self.tarea.iniciar()
