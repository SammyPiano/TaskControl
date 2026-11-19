# 6. Viáticos: solicitud, gastos y liquidación

[← Volver al índice](../EXPLICACION.md)

Un **viático** es dinero que la empresa le da a un empleado para los gastos de una tarea (combustible,
peajes, comida, materiales…). El ciclo completo es:

1. El empleado **solicita** un monto para una de sus tareas.
2. El administrador lo **autoriza** (con un monto aprobado) o lo **rechaza** (con motivo).
3. Opcionalmente, el administrador le da un **anticipo** (dinero por adelantado).
4. El empleado **registra cada gasto** con la foto del comprobante.
5. El administrador **aprueba o rechaza** cada gasto.
6. El administrador **liquida**: calcula el saldo y decide si la empresa reembolsa o el empleado devuelve.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `Viatico`, `Gasto` y `Liquidacion`, con todos los métodos de estado |
| `api.py` | Vistas de `/api/viaticos/…` y `/api/gastos/…` |
| `urls_api.py` | Las 11 rutas de la API de viáticos |
| `forms.py` | `GastoForm`: valida el gasto y procesa la foto del comprobante |
| `admin.py` | Panel `/admin/` en solo lectura (los cambios de estado se hacen desde la app) |
| `migrations/0001_initial.py` | Crea las tablas, incluida una **restricción** de base de datos para la regla 7 |
| `tests.py` | Pruebas de las reglas 3, 5, 6 y 7 aplicadas a viáticos |

### Cómo se relacionan los modelos

```text
Tarea 1 ── * Viatico 1 ── * Gasto (con foto del comprobante)
                │
                └── 0..1 Liquidacion (total de gastos, anticipo, saldo y resultado)
```

---

## Fragmentos importantes

### 6.1 `models.py` — utilidades del archivo

```python
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
```

- `CERO = Decimal("0.00")` — el cero como `Decimal`. Para dinero **nunca** se usa `float`, porque `0.1 + 0.2` en `float` da `0.30000000000000004`; `Decimal` hace las cuentas exactas.
- `MONTO_POSITIVO = [MinValueValidator(Decimal("0.01"))]` — validador reutilizable: el monto debe ser al menos 0.01.
- `def _monto(**kwargs):` — atajo para crear un campo de dinero: hasta 12 dígitos con 2 decimales (hasta RD$ 9 999 999 999.99). `**kwargs` pasa cualquier opción extra.
- `def _validar_admin(usuario, tarea):` — lanza un error si quien actúa no es administrador **de la empresa de la tarea**. La usan todos los métodos de administrador.
- `def _exigir_observacion(observacion, mensaje):` — **regla 3**: si la observación está vacía, lanza el error; si no, la devuelve sin espacios.

### 6.2 `models.py` — el viático y la regla 7 en la base de datos

```python
class Viatico(models.Model):
    class Estado(models.TextChoices):
        SOLICITADO = "SOLICITADO", "Solicitado"
        AUTORIZADO = "AUTORIZADO", "Autorizado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        ANTICIPO_ENTREGADO = "ANTICIPO_ENTREGADO", "Anticipo entregado"
        EN_COMPROBACION = "EN_COMPROBACION", "En comprobación"
        LIQUIDADO = "LIQUIDADO", "Liquidado"

    ESTADOS_GASTOS = (Estado.AUTORIZADO, Estado.ANTICIPO_ENTREGADO, Estado.EN_COMPROBACION)

    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name="viaticos")
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="viaticos")
    concepto = models.CharField(max_length=255)
    monto_solicitado = _monto(verbose_name="monto solicitado", validators=MONTO_POSITIVO)
    monto_aprobado = _monto(verbose_name="monto aprobado", null=True, blank=True)
    anticipo_entregado = _monto(verbose_name="anticipo entregado", default=CERO)
    estado = models.CharField(max_length=18, choices=Estado.choices, default=Estado.SOLICITADO)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(anticipo_entregado=0)
                | models.Q(monto_aprobado__isnull=False, anticipo_entregado__lte=models.F("monto_aprobado")),
                name="viatico_anticipo_no_supera_aprobado",
            ),
        ]
```

- `class Estado(...)` — los 6 estados del viático (ver el diagrama del [índice](../EXPLICACION.md#44-los-estados-máquinas-de-estado)).
- `ESTADOS_GASTOS = (...)` — estados en los que el empleado puede registrar gastos y el administrador puede liquidar.
- `tarea`, `empleado` — a qué tarea pertenece y quién lo pidió.
- `concepto` — para qué es ("Combustible y peajes").
- `monto_solicitado = _monto(..., validators=MONTO_POSITIVO)` — lo que pidió el empleado (mayor que 0).
- `monto_aprobado = _monto(..., null=True, blank=True)` — lo que aprobó el administrador; vacío hasta que se autorice.
- `anticipo_entregado = _monto(..., default=CERO)` — dinero entregado por adelantado.
- `estado = ... default=Estado.SOLICITADO` — nace como solicitud.
- `models.CheckConstraint(...)` — una **regla que la propia base de datos hace cumplir** (**regla 7**). Dice: "el anticipo es 0, **o** hay monto aprobado y el anticipo es menor o igual que él". `models.F("monto_aprobado")` se refiere al valor de otra columna de la misma fila. Aunque alguien se saltara el código de Python, la base de datos rechazaría el dato.

### 6.3 `models.py` — bloquear antes de cambiar

```python
    def _bloquear(self, *estados):
        """Bloquea la fila y verifica que el estado actual esté entre `estados`."""
        actual = Viatico.objects.select_for_update().select_related("tarea").get(pk=self.pk)
        if actual.estado not in estados:
            raise ValidationError(f"El viático está {actual.get_estado_display().lower()}; la acción no aplica.")
        return actual
```

- `def _bloquear(self, *estados):` — `*estados` recibe cualquier cantidad de estados permitidos.
- `actual = Viatico.objects.select_for_update()...get(pk=self.pk)` — relee el viático **bloqueándolo** hasta que termine la transacción, para que dos acciones no lo cambien a la vez.
- `if actual.estado not in estados: raise ValidationError(...)` — si el viático no está en un estado donde la acción tenga sentido (por ejemplo, autorizar uno ya liquidado), lo impide con un mensaje claro.
- `return actual` — devuelve la copia fresca y bloqueada, que es la que se modifica.

### 6.4 `models.py` — autorizar (regla 7)

```python
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
```

- `anticipo = anticipo or CERO` — si no se mandó anticipo (`None`), usa 0.
- `actual = self._bloquear(self.Estado.SOLICITADO)` — solo se autoriza lo que está **solicitado**.
- `_validar_admin(admin, actual.tarea)` — solo un administrador de esa empresa.
- `if monto_aprobado is None or monto_aprobado <= 0: raise ...` — el aprobado debe ser positivo.
- `if anticipo < 0: raise ...` — el anticipo no puede ser negativo.
- `if anticipo > monto_aprobado: raise ...` — **regla 7**, con un mensaje claro (la restricción de la base de datos es el último seguro).
- `actual.monto_aprobado = ...`, `autorizado_por`, `autorizado_en`, `anticipo_entregado` — guarda quién, cuándo y cuánto.
- `actual.estado = self.Estado.ANTICIPO_ENTREGADO if anticipo > 0 else self.Estado.AUTORIZADO` — si dio anticipo, salta directo a "Anticipo entregado"; si no, queda "Autorizado".
- `actual.save()` — guarda.
- `registrar(...)` — **regla 8**: "Solicitado → Anticipo entregado. Aprobado RD$ 1,500.00, anticipo RD$ 1,500.00."
- `actual._avisar_empleado(...)` — notificación al empleado con enlace al viático.
- `self.refresh_from_db()` — actualiza el objeto original (`self`) con lo que quedó guardado, para que quien llamó vea los datos nuevos.

### 6.5 `models.py` — registrar un gasto

```python
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
            notificar_administradores(...)
        self.refresh_from_db()
        return gasto
```

- `actual = self._bloquear(*self.ESTADOS_GASTOS)` — `*` "desempaca" la tupla: es como escribir `_bloquear(AUTORIZADO, ANTICIPO_ENTREGADO, EN_COMPROBACION)`.
- `if empleado.pk != actual.empleado_id: raise ...` — solo el dueño del viático registra gastos.
- `if monto is None or monto <= 0: raise ...` — monto positivo.
- `if fecha > timezone.localdate(): raise ...` — no se aceptan gastos con fecha futura.
- `gasto = Gasto.objects.create(...)` — crea el gasto en estado PENDIENTE (valor por defecto).
- `detalle = f"Gasto #{gasto.pk} (...)."` — texto para el historial.
- `if anterior != self.Estado.EN_COMPROBACION:` — con el **primer** gasto…
- `actual.estado = self.Estado.EN_COMPROBACION` — …el viático pasa a "En comprobación".
- `registrar(...)` / `notificar_administradores(...)` — historial y aviso a los administradores.
- `return gasto` — devuelve el gasto creado.

### 6.6 `models.py` — liquidar (regla 6)

```python
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
            ...
        self.refresh_from_db()
        return liquidacion
```

- `actual = self._bloquear(*self.ESTADOS_GASTOS)` — se puede liquidar un viático autorizado, con anticipo o en comprobación (no uno solicitado, rechazado o ya liquidado).
- `_validar_admin(...)` — solo administradores de la empresa.
- `if actual.gastos.filter(estado=Gasto.Estado.PENDIENTE).exists(): raise ...` — **regla 6**: no se liquida con gastos sin revisar.
- `total_gastos = actual.totales()[Gasto.Estado.APROBADO]` — suma **solo** los gastos aprobados (los rechazados no cuentan).
- `saldo = total_gastos - actual.anticipo_entregado` — **la fórmula de la regla 6**.
- `if saldo > 0: resultado = REEMBOLSO` — el empleado gastó más de lo que recibió: la empresa le debe.
- `elif saldo < 0: resultado = DEVOLUCION` — recibió más de lo que gastó: devuelve la diferencia.
- `else: resultado = SALDADO` — quedó exacto.
- `liquidacion = Liquidacion.objects.create(...)` — guarda la liquidación con todos los números (así queda constancia aunque luego cambie algo).
- `actual.estado = self.Estado.LIQUIDADO` — el viático se cierra.
- (líneas omitidas) — anota en el historial y avisa al empleado: "Reembolso al empleado: RD$ 350.00".

**Ejemplo:** anticipo RD$ 2,000; gastos aprobados RD$ 2,350 → saldo = 2,350 − 2,000 = **+350** → la empresa reembolsa RD$ 350.

### 6.7 `api.py` — una vista para cuatro acciones

```python
class AccionView(APIView):
    """Autorizar, rechazar, entregar anticipo y liquidar: la lógica está en los métodos del modelo."""

    permission_classes = [EsAdministrador]
    accion = None

    def post(self, request, pk):
        viatico = get_object_or_404(viaticos_visibles(request.user), pk=pk)
        d = request.data
        if self.accion == "autorizar":
            aprobado = decimal(d.get("monto_aprobado"))
            anticipo = decimal(d.get("anticipo"), opcional=True)
            if aprobado is None or anticipo is None:
                return Response({"detail": ["Indique montos válidos."]}, status=400)
            viatico.autorizar(request.user, aprobado, anticipo)
        elif self.accion == "rechazar":
            viatico.rechazar(request.user, d.get("observacion", ""))
        elif self.accion == "anticipo":
            ...
            viatico.entregar_anticipo(request.user, anticipo)
        elif self.accion == "liquidar":
            viatico.liquidar(request.user)
        return responder_detalle(request, pk)
```

- `class AccionView(APIView):` — una sola clase sirve para 4 rutas distintas.
- `accion = None` — se configura en `urls_api.py`: `api.AccionView.as_view(accion="autorizar")`, `as_view(accion="liquidar")`, etc.
- `viatico = get_object_or_404(viaticos_visibles(request.user), pk=pk)` — el viático debe ser de su empresa (regla 5).
- `d = request.data` — los datos que envió React.
- `if self.accion == "autorizar":` — según la acción configurada…
- `aprobado = decimal(d.get("monto_aprobado"))` — convierte el texto a `Decimal` (la función `decimal` de este archivo acepta "1,500.00" y devuelve `None` si no es un número).
- `if aprobado is None or anticipo is None: return Response(..., status=400)` — montos inválidos.
- `viatico.autorizar(request.user, aprobado, anticipo)` — **la vista no decide nada**: solo traduce los datos y llama al modelo.
- `return responder_detalle(request, pk)` — devuelve el viático actualizado; la pantalla se refresca con él.

### 6.8 `api.py` — el resumen del empleado

```python
    @staticmethod
    def resumen(empleado):
        """Sobre los viáticos abiertos: lo aprobado y el anticipo que aún no cubren los gastos registrados."""
        disponible = por_comprobar = CERO
        abiertos = viaticos_visibles(empleado).filter(estado__in=Viatico.ESTADOS_GASTOS).annotate(
            registrado=Sum("gastos__monto", filter=~Q(gastos__estado=Gasto.Estado.RECHAZADO))
        )
        for v in abiertos:
            registrado = v.registrado or CERO
            disponible += max((v.monto_aprobado or CERO) - registrado, CERO)
            por_comprobar += max(v.anticipo_entregado - registrado, CERO)
        return {"disponible": monto(disponible), "por_comprobar": monto(por_comprobar)}
```

- `@staticmethod` — método que no usa `self`; se llama como `ViaticosView.resumen(usuario)`.
- `disponible = por_comprobar = CERO` — dos acumuladores en cero.
- `abiertos = ... .filter(estado__in=Viatico.ESTADOS_GASTOS)` — los viáticos del empleado que siguen abiertos.
- `.annotate(registrado=Sum("gastos__monto", filter=~Q(...RECHAZADO)))` — suma los gastos de cada viático **sin contar los rechazados**. `~Q(...)` significa "NO".
- `for v in abiertos:` — recorre cada viático.
- `disponible += max(aprobado - registrado, CERO)` — cuánto le queda por gastar (nunca negativo).
- `por_comprobar += max(anticipo - registrado, CERO)` — cuánto anticipo aún no justifica con comprobantes.
- `return {...}` — son las dos cifras de la tarjeta verde de la pantalla "Mis viáticos".

---

## Cómo se conecta con lo demás

- Cuelga de **tareas** (`Viatico.tarea`) y solo el empleado asignado a la tarea puede pedirlo.
- Usa **historial** (`registrar`, `notificar`, `notificar_administradores`, `rd`, `cambio`).
- Usa `gestion_campo/imagenes.py` para la foto del comprobante y `servir_archivo` para mostrarla protegida.
- **reportes** suma solicitudes, anticipos, gastos y liquidaciones por empleado.
- En el frontend: `pages/empleado/MisViaticos.tsx`, `SolicitarViatico.tsx`, `ViaticoDetalle.tsx`, `RegistrarGasto.tsx`
  y `pages/admin/Viaticos.tsx`, `ViaticoDetalle.tsx`.

[← Anterior: Entregas](05-entregas.md) · [Índice](../EXPLICACION.md) · [Siguiente: Historial →](07-historial.md)
