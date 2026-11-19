# 5. Entregas: evidencias y revisión

[← Volver al índice](../EXPLICACION.md)

Cuando el empleado termina una tarea, hace una **entrega**: manda fotos como **evidencia** y un comentario.
El administrador la **revisa**: la **aprueba** (la tarea queda completada) o la **devuelve** con una
observación (el empleado corrige y manda una **nueva versión**).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `Entrega`, `Evidencia` y `Revision`, con `presentar()`, `aprobar()` y `devolver()` |
| `api.py` | Vistas: bandeja de revisión, detalle, aprobar, devolver, presentar y servir fotos |
| `urls_api.py` | Las 6 rutas de la API de entregas |
| `forms.py` | `EntregaForm`: recibe varias fotos, las valida y las achica con `procesar_imagen` |
| `admin.py` | Panel `/admin/` (solo lectura: los cambios se hacen desde la aplicación) |
| `migrations/0001_initial.py` | Crea las tablas |
| `tests.py` | Pruebas de las reglas 1, 2, 3, 4 y 5 aplicadas a entregas |

### Cómo se relacionan los modelos

```text
Tarea 1 ── * Entrega (versión 1, 2, 3…) 1 ── * Evidencia (fotos)
                       │
                       └── 0..1 Revision (aprobada o devuelta, con observaciones)
```

---

## Fragmentos importantes

### 5.1 `models.py` — la entrega y sus versiones

```python
class Entrega(models.Model):
    class Estado(models.TextChoices):
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADA = "APROBADA", "Aprobada"
        DEVUELTA = "DEVUELTA", "Devuelta"

    # Versiones y evidencias nunca se borran (PROTECT)
    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name="entregas")
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entregas")
    version = models.PositiveIntegerField("versión")
    comentario = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.EN_REVISION)
    presentada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["tarea", "version"], name="entrega_version_unica")]
```

- `class Estado(models.TextChoices):` — una entrega está en revisión, aprobada o devuelta.
- `tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, ...)` — `PROTECT` impide borrar una tarea que tenga entregas: **regla 4**, nunca se pierden versiones.
- `empleado = ...` — quién la presentó.
- `version = models.PositiveIntegerField("versión")` — 1 para la primera, 2 para la que se manda tras una devolución, etc.
- `comentario` — texto opcional del empleado.
- `estado = ... default=Estado.EN_REVISION` — al presentarse, queda en revisión.
- `presentada_en = models.DateTimeField(default=timezone.now)` — fecha y hora de la entrega.
- `ordering = ["-version"]` — se listan de la más nueva a la más vieja (el `-` invierte el orden).
- `UniqueConstraint(fields=["tarea", "version"], ...)` — una tarea no puede tener dos entregas con la misma versión.

### 5.2 `models.py` — presentar una entrega (regla 2)

```python
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
```

- `@classmethod` — método de la **clase** (no de una entrega concreta), porque crea una entrega nueva. `cls` es la clase `Entrega`.
- `with transaction.atomic():` — todo o nada: la entrega, las fotos, el cambio de la tarea y el historial.
- `tarea = Tarea.objects.select_for_update().get(pk=tarea.pk)` — vuelve a leer la tarea **bloqueándola**: si el empleado pulsa "enviar" dos veces seguidas, la segunda espera a que termine la primera y entonces verá que ya está en revisión.
- `if empleado.pk != tarea.asignado_a_id: raise ValidationError(...)` — solo el empleado asignado puede entregar.
- `if not tarea.esta_abierta: raise ValidationError(...)` — no se entrega una tarea que ya está en revisión o completada.
- `pendientes = tarea.obligatorios_pendientes()` — **regla 2, parte 1**: busca ítems obligatorios sin marcar.
- `raise ValidationError("Complete los ítems obligatorios...: " + ", ".join(...))` — si hay, rechaza y dice cuáles faltan.
- `if not evidencias: raise ValidationError(...)` — **regla 2, parte 2**: al menos una foto.
- `ultima = tarea.entregas.aggregate(m=Max("version"))["m"] or 0` — busca la versión más alta que ya existe (o 0 si es la primera).
- `entrega = cls.objects.create(..., version=ultima + 1, ...)` — crea la nueva versión (**regla 4**).
- `for archivo, descripcion in evidencias: Evidencia.objects.create(...)` — guarda cada foto ligada a la entrega.
- `anterior = tarea.estado` — recuerda el estado anterior para el historial.
- `tarea.estado = Tarea.Estado.EN_REVISION` / `tarea.save(...)` — la tarea pasa a "En revisión".
- `registrar(empleado, tarea, "Entrega presentada", ...)` — **regla 8**.
- `notificar_administradores(...)` — avisa a todos los administradores de la empresa con enlace a la entrega.
- `return entrega` — devuelve la entrega creada.

### 5.3 `models.py` — aprobar o devolver (reglas 1, 3 y 4)

```python
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
```

- `def aprobar(...)` — atajo que llama a `_revisar` con la decisión "APROBADA". La observación es opcional.
- `def devolver(...)` — **regla 3**: si la observación está vacía (o solo tiene espacios), rechaza.
- `return self._revisar(revisor, Revision.Decision.DEVUELTA, observaciones)` — si hay observación, revisa con decisión "DEVUELTA".
- `def _revisar(...)` — la lógica común de ambas decisiones (el `_` indica que es interna).
- `tarea = Tarea.objects.select_for_update().get(...)` — bloquea la tarea.
- `estado_actual = Entrega.objects.select_for_update().values_list("estado", flat=True).get(pk=self.pk)` — bloquea la entrega y lee su estado **actual en la base de datos** (no el que tenía la variable al cargarse).
- `if estado_actual != self.Estado.EN_REVISION: raise ValidationError("Esta entrega ya fue revisada.")` — evita que dos administradores la revisen a la vez.
- `if not revisor.es_administrador or revisor.empresa_id != tarea.empresa_id: raise ...` — doble seguro: aunque la vista ya revisó el permiso, el modelo también lo exige.
- `revision = Revision.objects.create(...)` — guarda quién revisó, qué decidió y por qué.
- `self.estado = decision` / `self.save(...)` — la entrega queda APROBADA o DEVUELTA.
- `if decision == Revision.Decision.APROBADA:` — **regla 1**: solo aquí la tarea pasa a COMPLETADA…
  - `tarea.completada_en = timezone.now()` — …y se guarda la hora en que se completó.
- `else: tarea.estado = Tarea.Estado.DEVUELTA` — si se devuelve, la tarea vuelve a estar abierta para que el empleado corrija.
- `tarea.save(update_fields=[...])` — guarda la tarea.
- `detalle = ...` / `registrar(...)` — **regla 8**: anota "Versión 1. En revisión → Completada. Observaciones: …".
- `notificar(tarea.asignado_a, aviso, "tarea", tarea.pk)` — avisa al empleado.
- `self.tarea = tarea` — actualiza la tarea en memoria por si quien llamó la quiere usar.

### 5.4 `forms.py` — recibir y validar varias fotos

```python
class EntregaForm(forms.Form):
    """Valida y redimensiona las fotos de una entrega (multipart: fotos[], descripciones[], comentario)."""

    comentario = forms.CharField(required=False)
    fotos = FotosField(required=False)

    def clean_fotos(self):
        fotos = self.cleaned_data["fotos"]
        if not fotos:
            raise ValidationError("Agregue al menos una foto como evidencia.")
        if len(fotos) > MAX_FOTOS:
            raise ValidationError(f"Puede adjuntar hasta {MAX_FOTOS} fotos por entrega.")
        evidencias, errores = [], []
        for i, foto in enumerate(fotos):
            descripcion = self.descripciones[i].strip()[:255] if i < len(self.descripciones) else ""
            try:
                evidencias.append((procesar_imagen(foto), descripcion))
            except ValidationError as e:
                errores.append(f"{foto.name}: {' '.join(e.messages)}")
        if errores:
            raise ValidationError(errores)
        return evidencias
```

- `class EntregaForm(forms.Form):` — un formulario de Django (no ligado a un modelo) para datos que llegan como `multipart/form-data` (el formato para subir archivos).
- `comentario = forms.CharField(required=False)` — texto opcional.
- `fotos = FotosField(required=False)` — campo propio (definido más arriba en el archivo) que acepta **varios** archivos con el mismo nombre.
- `def clean_fotos(self):` — Django llama automáticamente a `clean_<campo>` para validar ese campo.
- `if not fotos: raise ValidationError(...)` — al menos una foto.
- `if len(fotos) > MAX_FOTOS: raise ValidationError(...)` — máximo 10.
- `evidencias, errores = [], []` — dos listas vacías: fotos válidas y mensajes de error.
- `for i, foto in enumerate(fotos):` — recorre cada foto con su posición `i`.
- `descripcion = ...` — toma la descripción que corresponde a esa foto, si se envió.
- `evidencias.append((procesar_imagen(foto), descripcion))` — valida y achica la foto (ver [documento 1](01-arranque-y-configuracion.md#17-imagenespy--validar-y-achicar-fotos)).
- `except ValidationError as e: errores.append(...)` — si una foto no sirve, guarda el error con su nombre y sigue con las demás.
- `if errores: raise ValidationError(errores)` — al final, si hubo errores, los informa todos juntos.
- `return evidencias` — lista de `(archivo procesado, descripción)` que recibirá `Entrega.presentar`.

### 5.5 `api.py` — presentar y servir fotos protegidas

```python
class PresentarView(APIView):
    """Regla 2: ítems obligatorios marcados y al menos una foto (lo valida Entrega.presentar)."""

    permission_classes = [EsEmpleado]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
        form = EntregaForm(request.data, request.FILES)
        if not form.is_valid():
            return Response({"detail": [m for errores in form.errors.values() for m in errores]}, status=400)
        Entrega.presentar(tarea, request.user, form.cleaned_data["fotos"], form.cleaned_data["comentario"])
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=pk)), status=201)


class EvidenciaArchivoView(APIView):
    """Sirve la foto solo a quien puede verla (regla 5)."""

    permission_classes = [EmpresaActiva]

    def get(self, request, pk):
        evidencias = filtrar_por_usuario(
            Evidencia.objects.all(), request.user, "entrega__tarea__empresa", "entrega__empleado"
        )
        return servir_archivo(get_object_or_404(evidencias, pk=pk).archivo)
```

- `class PresentarView(APIView):` — `POST /api/tareas/<pk>/entregas/`.
- `permission_classes = [EsEmpleado]` — solo empleados.
- `parser_classes = [MultiPartParser, FormParser]` — esta vista acepta datos con archivos (no JSON).
- `tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)` — la tarea debe ser **suya** (regla 5).
- `form = EntregaForm(request.data, request.FILES)` — `request.FILES` trae las fotos.
- `if not form.is_valid(): return Response({...}, status=400)` — si las fotos no sirven, responde 400 con **todos** los mensajes en una lista plana. `[m for errores in ... for m in errores]` es una comprensión de lista doble que "aplana" los errores de cada campo.
- `Entrega.presentar(...)` — el modelo valida las reglas y guarda.
- `return Response(..., status=201)` — devuelve la tarea actualizada.
- `class EvidenciaArchivoView(APIView):` — `GET /api/evidencias/<pk>/archivo/`.
- `evidencias = filtrar_por_usuario(Evidencia.objects.all(), request.user, "entrega__tarea__empresa", "entrega__empleado")` — un administrador ve las fotos de su empresa; un empleado, solo las de **sus** entregas. Fíjate en cómo `__` recorre las relaciones: evidencia → entrega → tarea → empresa.
- `return servir_archivo(get_object_or_404(evidencias, pk=pk).archivo)` — si la foto está entre las permitidas, la envía; si no, 404.

---

## Cómo se conecta con lo demás

- Reutiliza de **tareas**: `tareas_visibles`, `detalle_qs`, `tarea_detalle` y `entrega_json`.
- Usa **historial** para `registrar`, `notificar` y `notificar_administradores`.
- Usa `gestion_campo/imagenes.py` para las fotos y `gestion_campo/api.py` para `servir_archivo`.
- **reportes** cuenta las devoluciones por empleado y muestra las entregas en revisión en el panel.
- En el frontend: `pages/empleado/Evidencias.tsx` (presentar), `pages/empleado/Entregas.tsx` (historial de versiones),
  `pages/admin/Revisiones.tsx` (bandeja) y `pages/admin/RevisarEntrega.tsx` (aprobar o devolver).

[← Anterior: Tareas](04-tareas.md) · [Índice](../EXPLICACION.md) · [Siguiente: Viáticos →](06-viaticos.md)
