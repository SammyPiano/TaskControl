# 4. Tareas y lista de verificación

[← Volver al índice](../EXPLICACION.md)

La app **`tareas`** es el corazón del sistema. Una **tarea** es una orden de trabajo: qué hay que hacer,
dónde, para cuándo, con qué prioridad y a qué empleado se le asignó. Cada tarea tiene su propia
**lista de verificación** (checklist): los pasos que el empleado va marcando.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `Tarea` e `ItemChecklist`, con los métodos que cambian el estado (`iniciar`, `marcar`…) |
| `api.py` | Vistas de `/api/tareas/`, `/api/mis-tareas/` y `/api/items/…/marcar/`, y funciones que arman el JSON |
| `urls_api.py` | Las 6 rutas de la API de tareas |
| `admin.py` | Configuración del panel `/admin/` |
| `migrations/0001_initial.py` | Crea las tablas de tareas e ítems |
| `tests.py` | Pruebas: crear y editar tareas, regla 5 (cada quien ve lo suyo), marcar ítems… |

---

## Fragmentos importantes

### 4.1 `models.py` — los estados y campos de una tarea

```python
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

    ESTADOS_ABIERTOS = (Estado.PENDIENTE, Estado.EN_PROCESO, Estado.DEVUELTA)

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="tareas")
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, related_name="tareas", ...)
    asignado_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tareas_asignadas", ...)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tareas_creadas")
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
```

- `class Prioridad(models.TextChoices):` — las 4 prioridades posibles.
- `class Estado(models.TextChoices):` — los 6 estados posibles de una tarea.
- `ESTADOS_ABIERTOS = (...)` — los estados en los que la tarea "está viva": el empleado puede marcar la lista y el administrador puede editarla. Se reutiliza en muchos lugares.
- `empresa = models.ForeignKey(Empresa, ...)` — la empresa dueña de la tarea (clave para la regla 5).
- `tipo_servicio = models.ForeignKey(TipoServicio, ...)` — el tipo de trabajo. `PROTECT` impide borrar un servicio en uso.
- `asignado_a = models.ForeignKey(settings.AUTH_USER_MODEL, ...)` — el empleado responsable. `settings.AUTH_USER_MODEL` es `"cuentas.Usuario"`; se escribe así para no atar el modelo a una clase concreta.
- `related_name="tareas_asignadas"` — desde un usuario: `usuario.tareas_asignadas.all()`.
- `creado_por = models.ForeignKey(...)` — el administrador que la creó. Como hay dos FK al mismo modelo `Usuario`, cada una necesita un `related_name` distinto.
- `titulo`, `descripcion`, `ubicacion`, `criterios_aceptacion` — textos. `TextField` es para textos largos sin límite.
- `prioridad = models.CharField(..., default=Prioridad.MEDIA)` — media si no se indica.
- `fecha_limite = models.DateField(null=True, blank=True)` — fecha (sin hora), opcional.
- `estado = models.CharField(..., default=Estado.PENDIENTE)` — toda tarea nace pendiente.
- `creada_en = models.DateTimeField(auto_now_add=True)` — se llena sola al crear.
- `actualizada_en = models.DateTimeField(auto_now=True)` — se actualiza sola cada vez que se guarda.
- `completada_en = models.DateTimeField(null=True, blank=True)` — se llena al aprobar la entrega.

### 4.2 `models.py` — propiedades calculadas

```python
    @property
    def codigo(self):
        return f"TC-{self.pk:04d}"

    @property
    def esta_abierta(self):
        return self.estado in self.ESTADOS_ABIERTOS

    @property
    def vencida(self):
        return bool(self.fecha_limite) and self.esta_abierta and self.fecha_limite < timezone.localdate()

    def obligatorios_pendientes(self):
        return list(self.items.filter(obligatorio=True, completado=False))
```

- `codigo` — un código legible para humanos: la tarea 7 es `"TC-0007"`. `:04d` rellena con ceros hasta 4 dígitos.
- `esta_abierta` — verdadero si el estado es uno de los abiertos.
- `vencida` — verdadero solo si: tiene fecha límite, **y** sigue abierta, **y** la fecha ya pasó. `timezone.localdate()` es "hoy" en Santo Domingo.
- `obligatorios_pendientes()` — lista de ítems obligatorios que faltan por marcar. La usa la **regla 2** al presentar una entrega.

### 4.3 `models.py` — crear la lista de verificación de una tarea nueva

```python
    @transaction.atomic
    def crear_checklist(self, items):
        """`items`: [{"descripcion", "obligatorio"}] editados desde la plantilla al crear la tarea."""
        ItemChecklist.objects.bulk_create(
            ItemChecklist(tarea=self, descripcion=d, obligatorio=bool(i.get("obligatorio", True)), orden=n)
            for n, (i, d) in enumerate(((i, str(i.get("descripcion", "")).strip()[:255]) for i in items), start=1)
            if d
        )
```

- `@transaction.atomic` — decorador: todo el método corre dentro de una transacción.
- `def crear_checklist(self, items):` — recibe la lista que armó el administrador en el formulario (copiada de la plantilla y quizás editada).
- `ItemChecklist.objects.bulk_create(...)` — crea todos los ítems en una sola consulta.
- `ItemChecklist(tarea=self, descripcion=d, obligatorio=..., orden=n)` — cada ítem nuevo, ligado a esta tarea.
- `for n, (i, d) in enumerate((... for i in items), start=1)` — recorre los ítems emparejando cada uno con su descripción limpia (`d`), y los numera desde 1 (`n`, el orden).
- `if d` — se salta los ítems con descripción vacía.

> Los ítems se **copian** a la tarea (tabla `ItemChecklist`). Por eso, cambiar la plantilla después no altera las tareas existentes.

### 4.4 `models.py` — iniciar la tarea y marcar ítems

```python
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

    @transaction.atomic
    def marcar(self, completado):
        if not self.tarea.esta_abierta:
            raise ValidationError("La tarea no admite cambios en el checklist en su estado actual.")
        self.completado = completado
        self.marcado_en = timezone.now() if completado else None
        self.save(update_fields=["completado", "marcado_en"])
        if completado:
            self.tarea.iniciar()
```

- `def iniciar(self):` — pasa la tarea de PENDIENTE a EN_PROCESO.
- `if self.estado == self.Estado.PENDIENTE:` — solo si estaba pendiente (si ya estaba en proceso, no hace nada).
- `self.estado = self.Estado.EN_PROCESO` / `self.save(update_fields=[...])` — cambia y guarda solo esas columnas.
- `registrar(self.asignado_a, self, "Iniciada", cambio(self, self.Estado.PENDIENTE))` — **regla 8**: lo anota en el historial con el texto "Pendiente → En proceso".
- `def registrar_asignacion(self, admin):` — al crear o reasignar la tarea:
  - `registrar(admin, self, "Asignada", ...)` — lo anota en el historial;
  - `notificar(self.asignado_a, ..., "tarea", self.pk)` — le manda una notificación al empleado con enlace a `/app/tareas/<id>`.
- `class ItemChecklist(models.Model):` — cada paso de la lista de una tarea.
- `tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="items")` — `CASCADE`: si se borrara la tarea, se borran sus ítems.
- `orden`, `obligatorio`, `completado`, `marcado_en` — posición, si es obligatorio, si ya se marcó y cuándo.
- `def marcar(self, completado):` — marca o desmarca el ítem.
- `if not self.tarea.esta_abierta: raise ValidationError(...)` — no se puede tocar la lista de una tarea en revisión o completada.
- `self.completado = completado` — guarda el nuevo valor (verdadero o falso).
- `self.marcado_en = timezone.now() if completado else None` — anota la hora al marcar; al desmarcar, la borra.
- `self.save(update_fields=[...])` — guarda.
- `if completado: self.tarea.iniciar()` — marcar el primer ítem **inicia** la tarea automáticamente.

### 4.5 `api.py` — qué tareas ve cada usuario (regla 5)

```python
def tareas_visibles(usuario):
    """Regla 5: el empleado solo las suyas; el administrador, las de su empresa."""
    return filtrar_por_usuario(Tarea.objects.all(), usuario, campo_propietario="asignado_a")


def con_progreso(queryset):
    return queryset.select_related("asignado_a", "tipo_servicio").annotate(
        items_total=Count("items", distinct=True),
        items_hechos=Count("items", filter=Q(items__completado=True), distinct=True),
    )
```

- `def tareas_visibles(usuario):` — **el único lugar** donde se decide qué tareas ve alguien. Todas las vistas parten de aquí.
- `filtrar_por_usuario(Tarea.objects.all(), usuario, campo_propietario="asignado_a")` — filtra por la empresa del usuario y, si es empleado, por `asignado_a = él` (ver [Cuentas](02-cuentas.md)).
- `def con_progreso(queryset):` — agrega el avance de la lista a cada tarea.
- `.select_related("asignado_a", "tipo_servicio")` — trae el empleado y el servicio en la misma consulta (un `JOIN` de SQL), en vez de una consulta extra por tarea.
- `.annotate(items_total=Count("items", distinct=True), ...)` — cuenta los ítems de cada tarea.
- `items_hechos=Count("items", filter=Q(items__completado=True), distinct=True)` — cuenta solo los marcados. `Q(...)` es una condición que se puede usar como filtro.

### 4.6 `api.py` — crear una tarea

```python
class TareasView(ListAPIView):
    """GET (administrador): lista filtrable de las tareas de su empresa. POST: crear y asignar."""

    permission_classes = [EsAdministrador]

    def post(self, request):
        serializer = TareaSerializer(data=request.data, empresa=request.user.empresa)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data.pop("items", [])
        with transaction.atomic():
            tarea = serializer.save(empresa=request.user.empresa, creado_por=request.user)
            tarea.crear_checklist(items)
            tarea.registrar_asignacion(request.user)
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=tarea.pk)), status=201)
```

- `class TareasView(ListAPIView):` — `ListAPIView` de DRF ya sabe listar y paginar; aquí además se agrega `post` para crear.
- `permission_classes = [EsAdministrador]` — solo administradores.
- `serializer = TareaSerializer(data=request.data, empresa=request.user.empresa)` — el serializer valida los datos. Recibe la empresa para que **solo acepte** tipos de servicio y empleados de esa empresa (si mandan un empleado de otra empresa, responde 400).
- `serializer.is_valid(raise_exception=True)` — si algo no es válido, responde 400 con los errores.
- `items = serializer.validated_data.pop("items", [])` — saca la lista de ítems (no es una columna de la tarea).
- `with transaction.atomic():` — crear la tarea, sus ítems y el historial juntos.
- `tarea = serializer.save(empresa=..., creado_por=request.user)` — crea la tarea. La empresa y el creador los pone **el servidor**, no los manda el navegador (así nadie puede crear tareas en otra empresa).
- `tarea.crear_checklist(items)` — crea su lista.
- `tarea.registrar_asignacion(request.user)` — historial + notificación al empleado.
- `return Response(tarea_detalle(...), status=201)` — devuelve la tarea completa con código 201.

### 4.7 `api.py` — marcar un ítem desde el teléfono

```python
class MarcarItemView(APIView):
    permission_classes = [EsEmpleado]

    def post(self, request, pk):
        item = get_object_or_404(
            ItemChecklist.objects.select_related("tarea"),
            pk=pk, tarea__empresa=request.user.empresa, tarea__asignado_a=request.user,
        )
        item.marcar(bool(request.data.get("completado")))
        return Response(tarea_detalle(detalle_qs(request.user).get(pk=item.tarea_id)))
```

- `permission_classes = [EsEmpleado]` — solo empleados marcan ítems.
- `def post(self, request, pk):` — `POST /api/items/<pk>/marcar/` con `{"completado": true}`.
- `get_object_or_404(..., pk=pk, tarea__empresa=..., tarea__asignado_a=request.user)` — busca el ítem **solo si** su tarea es de la empresa del empleado y está asignada a él. Si no, 404.
- `item.marcar(bool(request.data.get("completado")))` — la lógica está en el modelo (incluida la validación de estado).
- `return Response(tarea_detalle(...))` — devuelve la tarea actualizada para que la pantalla se refresque con el nuevo avance.

### 4.8 `tests.py` — cómo se prueba una regla

```python
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="A", rnc="101000001")
        cls.otra = Empresa.objects.create(nombre="B", rnc="101000002")
        cls.admin = Usuario.objects.create_user("admin", empresa=cls.empresa, rol=Usuario.Rol.ADMINISTRADOR)
        cls.emp = Usuario.objects.create_user("emp", empresa=cls.empresa)
        ...

class CrearTareaTests(Base):
    def test_empleado_no_crea(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.crear().status_code, 403)
```

- `class Base(TestCase):` — clase base con los datos que comparten las pruebas. `TestCase` crea una base de datos temporal y la limpia después de cada prueba.
- `def setUpTestData(cls):` — se ejecuta una vez y prepara: dos empresas (para probar que no se mezclan), un administrador, empleados, un servicio y una plantilla.
- `class CrearTareaTests(Base):` — un grupo de pruebas que hereda esos datos.
- `def test_empleado_no_crea(self):` — cada método que empieza con `test_` es una prueba.
- `self.client.force_login(self.emp)` — `self.client` es un navegador falso; `force_login` inicia sesión sin contraseña.
- `self.assertEqual(self.crear().status_code, 403)` — intenta crear una tarea por la API y **comprueba** que la respuesta sea 403 (prohibido). Si fuera otro código, la prueba falla y avisa.

> Las 104 pruebas del proyecto se corren con `pnpm django test` (o `python manage.py test`).

---

## Cómo se conecta con lo demás

- Usa **`configuracion`** (tipo de servicio), **`cuentas`** (empresa, empleado) e **`historial`** (`registrar`, `notificar`, `cambio`).
- **`entregas`** reutiliza `tareas_visibles`, `detalle_qs`, `tarea_detalle` y `entrega_json` de este `api.py`.
- **`viaticos`** cuelga de una tarea (`Viatico.tarea`).
- **`reportes`** cuenta tareas por estado y fecha.
- En el frontend: `pages/empleado/MisTareas.tsx` y `TareaDetalle.tsx` (empleado) y `pages/admin/Tareas.tsx`, `TareaDetalle.tsx` y `TareaForm.tsx` (administrador).

[← Anterior: Configuración](03-configuracion.md) · [Índice](../EXPLICACION.md) · [Siguiente: Entregas →](05-entregas.md)
