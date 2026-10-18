from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from gestion_campo.imagenes import validar_tamano
from historial.servicios import cambio, notificar, notificar_administradores, registrar, rd
from tareas.models import Tarea

CERO = Decimal("0.00")
MONTO_POSITIVO = [MinValueValidator(Decimal("0.01"))]


def _monto(**kwargs):
    return models.DecimalField(max_digits=12, decimal_places=2, **kwargs)


def _validar_admin(usuario, tarea):
    if not usuario.es_administrador or usuario.empresa_id != tarea.empresa_id:
        raise ValidationError("Solo un administrador de la empresa puede realizar esta acción.")


def _exigir_observacion(observacion, mensaje):
    observacion = (observacion or "").strip()
    if not observacion:
        raise ValidationError(mensaje)
    return observacion


class Viatico(models.Model):
    class Estado(models.TextChoices):
        SOLICITADO = "SOLICITADO", "Solicitado"
        AUTORIZADO = "AUTORIZADO", "Autorizado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        ANTICIPO_ENTREGADO = "ANTICIPO_ENTREGADO", "Anticipo entregado"
        EN_COMPROBACION = "EN_COMPROBACION", "En comprobación"
        LIQUIDADO = "LIQUIDADO", "Liquidado"

    # Estados en que el empleado puede registrar gastos y el administrador liquidar
    ESTADOS_GASTOS = (Estado.AUTORIZADO, Estado.ANTICIPO_ENTREGADO, Estado.EN_COMPROBACION)

    COLOR_ESTADO = {
        Estado.SOLICITADO: "info",
        Estado.AUTORIZADO: "primary",
        Estado.RECHAZADO: "danger",
        Estado.ANTICIPO_ENTREGADO: "primary",
        Estado.EN_COMPROBACION: "warning",
        Estado.LIQUIDADO: "success",
    }

    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name="viaticos")
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="viaticos")
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="viaticos_autorizados",
        null=True, blank=True, verbose_name="autorizado por",
    )
    concepto = models.CharField(max_length=255)
    monto_solicitado = _monto(verbose_name="monto solicitado", validators=MONTO_POSITIVO)
    monto_aprobado = _monto(verbose_name="monto aprobado", null=True, blank=True)
    anticipo_entregado = _monto(verbose_name="anticipo entregado", default=CERO)
    estado = models.CharField(max_length=18, choices=Estado.choices, default=Estado.SOLICITADO)
    observacion = models.TextField("observación", blank=True)
    solicitado_en = models.DateTimeField(default=timezone.now)
    autorizado_en = models.DateTimeField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-solicitado_en"]
        verbose_name = "viático"
        verbose_name_plural = "viáticos"
        indexes = [models.Index(fields=["estado", "solicitado_en"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(anticipo_entregado=0)
                | models.Q(monto_aprobado__isnull=False, anticipo_entregado__lte=models.F("monto_aprobado")),
                name="viatico_anticipo_no_supera_aprobado",
            ),
        ]

    def __str__(self):
        return f"{self.concepto} · {self.tarea}"

    @property
    def color_estado(self):
        return self.COLOR_ESTADO.get(self.estado, "secondary")

    @property
    def codigo(self):
        return f"VIA-{self.pk:04d}"

    @property
    def admite_gastos(self):
        return self.estado in self.ESTADOS_GASTOS

    def totales(self):
        """Suma de gastos por estado (PENDIENTE, APROBADO, RECHAZADO)."""
        sumas = dict(self.gastos.values_list("estado").annotate(t=Sum("monto")).order_by())
        return {estado: sumas.get(estado, CERO) for estado in Gasto.Estado.values}

    def _bloquear(self, *estados):
        """Bloquea la fila y verifica que el estado actual esté entre `estados`."""
        actual = Viatico.objects.select_for_update().select_related("tarea").get(pk=self.pk)
        if actual.estado not in estados:
            raise ValidationError(f"El viático está {actual.get_estado_display().lower()}; la acción no aplica.")
        return actual

    @classmethod
    def solicitar(cls, tarea, empleado, concepto, monto_solicitado):
        if empleado.pk != tarea.asignado_a_id:
            raise ValidationError("Solo el empleado asignado a la tarea puede solicitar viáticos.")
        if tarea.estado in (Tarea.Estado.COMPLETADA, Tarea.Estado.CANCELADA):
            raise ValidationError("La tarea ya está cerrada.")
        if monto_solicitado is None or monto_solicitado <= 0:
            raise ValidationError("El monto solicitado debe ser mayor que cero.")
        with transaction.atomic():
            viatico = cls.objects.create(
                tarea=tarea, empleado=empleado, concepto=concepto.strip(), monto_solicitado=monto_solicitado
            )
            registrar(empleado, viatico, "Solicitado", f"{viatico.concepto}: {rd(monto_solicitado)}.")
            notificar_administradores(
                tarea.empresa_id, f"{empleado} solicitó viático «{viatico.concepto}» por {rd(monto_solicitado)}.",
                "viatico", viatico.pk,
            )
        return viatico

    def _avisar_empleado(self, mensaje):
        notificar(self.empleado, mensaje, "viatico", self.pk)

    def autorizar(self, admin, monto_aprobado, anticipo=CERO):
        """Autoriza el monto; si se indica anticipo, queda entregado en el mismo paso (regla 7)."""
        anticipo = anticipo or CERO
        with transaction.atomic():
            actual = self._bloquear(self.Estado.SOLICITADO)
            _validar_admin(admin, actual.tarea)
            if monto_aprobado is None or monto_aprobado <= 0:
                raise ValidationError("El monto aprobado debe ser mayor que cero.")
            if anticipo < 0:
                raise ValidationError("El anticipo no puede ser negativo.")
            if anticipo > monto_aprobado:
                raise ValidationError("El anticipo no puede superar el monto aprobado.")
            actual.monto_aprobado = monto_aprobado
            actual.autorizado_por = admin
            actual.autorizado_en = timezone.now()
            actual.anticipo_entregado = anticipo
            actual.estado = self.Estado.ANTICIPO_ENTREGADO if anticipo > 0 else self.Estado.AUTORIZADO
            actual.save()
            montos = f"Aprobado {rd(monto_aprobado)}, anticipo {rd(anticipo)}"
            registrar(admin, actual, "Autorizado", f"{cambio(actual, self.Estado.SOLICITADO)}. {montos}.")
            actual._avisar_empleado(f"Viático «{actual.concepto}» autorizado. {montos}.")
        self.refresh_from_db()

    def entregar_anticipo(self, admin, anticipo):
        """Anticipo posterior a la autorización (regla 7)."""
        with transaction.atomic():
            actual = self._bloquear(self.Estado.AUTORIZADO)
            _validar_admin(admin, actual.tarea)
            if anticipo is None or anticipo <= 0:
                raise ValidationError("El anticipo debe ser mayor que cero.")
            if anticipo > actual.monto_aprobado:
                raise ValidationError("El anticipo no puede superar el monto aprobado.")
            actual.anticipo_entregado = anticipo
            actual.estado = self.Estado.ANTICIPO_ENTREGADO
            actual.save()
            registrar(admin, actual, "Anticipo entregado", f"{cambio(actual, self.Estado.AUTORIZADO)}. {rd(anticipo)}.")
            actual._avisar_empleado(f"Anticipo de {rd(anticipo)} entregado para «{actual.concepto}».")
        self.refresh_from_db()

    def rechazar(self, admin, observacion):
        """Regla 3: exige observación."""
        observacion = _exigir_observacion(observacion, "Indique el motivo del rechazo.")
        with transaction.atomic():
            actual = self._bloquear(self.Estado.SOLICITADO)
            _validar_admin(admin, actual.tarea)
            actual.estado = self.Estado.RECHAZADO
            actual.observacion = observacion
            actual.autorizado_por = admin
            actual.autorizado_en = timezone.now()
            actual.save()
            registrar(admin, actual, "Rechazado", f"{cambio(actual, self.Estado.SOLICITADO)}. Motivo: {observacion}")
            actual._avisar_empleado(f"Viático «{actual.concepto}» rechazado: {observacion}")
        self.refresh_from_db()

    def registrar_gasto(self, empleado, comprobante, categoria, fecha, monto, descripcion=""):
        with transaction.atomic():
            actual = self._bloquear(*self.ESTADOS_GASTOS)
            if empleado.pk != actual.empleado_id:
                raise ValidationError("Solo el empleado del viático puede registrar gastos.")
            if monto is None or monto <= 0:
                raise ValidationError("El monto del gasto debe ser mayor que cero.")
            if fecha > timezone.localdate():
                raise ValidationError("La fecha del gasto no puede ser futura.")
            gasto = Gasto.objects.create(
                viatico=actual, categoria=categoria, fecha=fecha, monto=monto,
                comprobante=comprobante, descripcion=descripcion.strip(),
            )
            detalle = f"Gasto #{gasto.pk} ({gasto.get_categoria_display()}, {rd(monto)})."
            anterior = actual.estado
            if anterior != self.Estado.EN_COMPROBACION:
                actual.estado = self.Estado.EN_COMPROBACION
                actual.save(update_fields=["estado", "actualizado_en"])
                detalle += f" {cambio(actual, anterior)}"
            registrar(empleado, actual, "Gasto registrado", detalle)
            notificar_administradores(
                actual.tarea.empresa_id,
                f"{empleado} registró un gasto de {rd(monto)} en «{actual.concepto}».",
                "viatico", actual.pk,
            )
        self.refresh_from_db()
        return gasto

    def liquidar(self, admin):
        """Regla 6: saldo = gastos aprobados − anticipo; no se liquida con gastos pendientes."""
        with transaction.atomic():
            actual = self._bloquear(*self.ESTADOS_GASTOS)
            _validar_admin(admin, actual.tarea)
            if actual.gastos.filter(estado=Gasto.Estado.PENDIENTE).exists():
                raise ValidationError("Revise todos los gastos pendientes antes de liquidar.")
            total_gastos = actual.totales()[Gasto.Estado.APROBADO]
            saldo = total_gastos - actual.anticipo_entregado
            if saldo > 0:
                resultado = Liquidacion.Resultado.REEMBOLSO
            elif saldo < 0:
                resultado = Liquidacion.Resultado.DEVOLUCION
            else:
                resultado = Liquidacion.Resultado.SALDADO
            liquidacion = Liquidacion.objects.create(
                viatico=actual, liquidado_por=admin, total_gastos=total_gastos,
                total_anticipo=actual.anticipo_entregado, saldo=saldo, resultado=resultado,
            )
            anterior = actual.estado
            actual.estado = self.Estado.LIQUIDADO
            actual.save(update_fields=["estado", "actualizado_en"])
            resumen = f"{liquidacion.get_resultado_display()}: {rd(abs(saldo))}"
            registrar(admin, actual, "Liquidado", (
                f"{cambio(actual, anterior)}. Gastos aprobados {rd(total_gastos)}, "
                f"anticipo {rd(actual.anticipo_entregado)}. {resumen}."
            ))
            actual._avisar_empleado(f"Viático «{actual.concepto}» liquidado. {resumen}.")
        self.refresh_from_db()
        return liquidacion


def ruta_comprobante(instancia, nombre):
    return f"comprobantes/{timezone.localdate():%Y/%m}/{nombre}"


class Gasto(models.Model):
    class Categoria(models.TextChoices):
        TRANSPORTE = "TRANSPORTE", "Transporte"
        COMBUSTIBLE = "COMBUSTIBLE", "Combustible"
        PEAJE = "PEAJE", "Peaje"
        ALIMENTACION = "ALIMENTACION", "Alimentación"
        HOSPEDAJE = "HOSPEDAJE", "Hospedaje"
        MATERIALES = "MATERIALES", "Materiales"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    COLOR_ESTADO = {Estado.PENDIENTE: "secondary", Estado.APROBADO: "success", Estado.RECHAZADO: "danger"}

    viatico = models.ForeignKey(Viatico, on_delete=models.PROTECT, related_name="gastos", verbose_name="viático")
    categoria = models.CharField("categoría", max_length=12, choices=Categoria.choices)
    fecha = models.DateField()
    monto = _monto(validators=MONTO_POSITIVO)
    descripcion = models.CharField("descripción", max_length=255, blank=True)
    comprobante = models.ImageField(upload_to=ruta_comprobante, validators=[validar_tamano])
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    observacion = models.TextField("observación", blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gastos_revisados", null=True, blank=True
    )
    revisado_en = models.DateTimeField(null=True, blank=True)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name = "gasto"
        verbose_name_plural = "gastos"

    def __str__(self):
        return f"{self.get_categoria_display()} · {self.monto}"

    @property
    def color_estado(self):
        return self.COLOR_ESTADO.get(self.estado, "secondary")

    def aprobar(self, admin, observacion=""):
        return self._revisar(admin, self.Estado.APROBADO, observacion)

    def rechazar(self, admin, observacion):
        """Regla 3: exige observación."""
        observacion = _exigir_observacion(observacion, "Indique el motivo del rechazo del gasto.")
        return self._revisar(admin, self.Estado.RECHAZADO, observacion)

    def _revisar(self, admin, estado, observacion):
        with transaction.atomic():
            viatico = self.viatico._bloquear(Viatico.Estado.EN_COMPROBACION)
            _validar_admin(admin, viatico.tarea)
            actual = Gasto.objects.select_for_update().get(pk=self.pk)
            if actual.estado != self.Estado.PENDIENTE:
                raise ValidationError("Este gasto ya fue revisado.")
            actual.estado = estado
            actual.observacion = (observacion or "").strip()
            actual.revisado_por = admin
            actual.revisado_en = timezone.now()
            actual.save()
            detalle = f"Gasto #{actual.pk} ({actual.get_categoria_display()}, {rd(actual.monto)}). "
            detalle += cambio(actual, self.Estado.PENDIENTE)
            if actual.observacion:
                detalle += f". Observación: {actual.observacion}"
            registrar(admin, viatico, f"Gasto {actual.get_estado_display().lower()}", detalle)
            if estado == self.Estado.RECHAZADO:
                viatico._avisar_empleado(
                    f"Gasto de {rd(actual.monto)} en «{viatico.concepto}» rechazado: {actual.observacion}"
                )
        self.refresh_from_db()


class Liquidacion(models.Model):
    class Resultado(models.TextChoices):
        REEMBOLSO = "REEMBOLSO", "Reembolso al empleado"
        DEVOLUCION = "DEVOLUCION", "Devolución a la empresa"
        SALDADO = "SALDADO", "Saldado"

    viatico = models.OneToOneField(Viatico, on_delete=models.PROTECT, related_name="liquidacion")
    liquidado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="liquidaciones")
    total_gastos = _monto(verbose_name="total de gastos aprobados")
    total_anticipo = _monto(verbose_name="total de anticipo")
    saldo = _monto()
    resultado = models.CharField(max_length=10, choices=Resultado.choices)
    liquidada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "liquidación"
        verbose_name_plural = "liquidaciones"

    def __str__(self):
        return f"{self.viatico} · {self.get_resultado_display()}"

    @property
    def saldo_absoluto(self):
        return abs(self.saldo)
