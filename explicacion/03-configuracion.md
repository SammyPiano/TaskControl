# 3. Configuración: tipos de servicio y plantillas

[← Volver al índice](../EXPLICACION.md)

La app **`configuracion`** guarda los **tipos de servicio** que ofrece cada empresa (por ejemplo,
"Mantenimiento de A/C" o "Limpieza profunda") y, para cada uno, una **plantilla de lista de verificación**:
los pasos que el técnico debe marcar. Al crear una tarea, el administrador parte de esa plantilla.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `TipoServicio`, `PlantillaChecklist`, `ItemPlantilla` y la función `guardar_plantilla()` |
| `api.py` | Vistas de `/api/servicios/`: listar, crear, renombrar, archivar y guardar la plantilla |
| `urls_api.py` | Las 3 rutas de la API |
| `admin.py` | Configuración del panel `/admin/` |
| `migrations/` | `0001_initial` crea las tablas; `0002_tiposervicio_activo` agrega el campo `activo` (para archivar) |
| `tests.py` | Pruebas de permisos, nombre único por empresa, guardado de plantillas y archivado de servicios con tareas |

### Cómo se relacionan los modelos

```text
Empresa 1 ── * TipoServicio 1 ── * PlantillaChecklist 1 ── * ItemPlantilla
                    │
                    └── * Tarea   (cada tarea es de un tipo de servicio)
```

---

## Fragmentos importantes

### 3.1 `models.py` — TipoServicio y su "borrado" inteligente

```python
class TipoServicio(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="tipos_servicio")
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nombre"], name="tiposervicio_unico_por_empresa"),
        ]

    def eliminar(self):
        """Sin tareas se borra; con tareas se archiva para que estas conserven su servicio. Devuelve True si se archivó."""
        if self.tareas.exists():
            self.activo = False
            self.save(update_fields=["activo"])
            return True
        self.delete()
        return False
```

- `empresa = models.ForeignKey(Empresa, ...)` — cada tipo de servicio pertenece a una empresa; dos empresas pueden tener servicios con el mismo nombre.
- `nombre = models.CharField(max_length=100)` — nombre del servicio.
- `activo = models.BooleanField(default=True)` — los servicios archivados quedan con `activo=False`.
- `constraints = [models.UniqueConstraint(fields=["empresa", "nombre"], ...)]` — la **base de datos** impide que una misma empresa tenga dos servicios con el mismo nombre.
- `def eliminar(self):` — método que decide **cómo** eliminar.
- `if self.tareas.exists():` — si alguna tarea usa este servicio (`tareas` viene del `related_name` en el modelo `Tarea`)…
- `self.activo = False` / `self.save(update_fields=["activo"])` — …no se borra: se **archiva**. `update_fields` guarda solo esa columna (más rápido y seguro).
- `return True` — avisa que se archivó.
- `self.delete()` / `return False` — si nadie lo usaba, se borra de verdad.

> ¿Por qué no borrar siempre? Porque las tareas antiguas apuntan a ese servicio (`on_delete=PROTECT` lo impediría)
> y perderían la información de qué tipo de trabajo eran.

### 3.2 `models.py` — guardar la plantilla

```python
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
```

- `def guardar_plantilla(tipo_servicio, items):` — recibe el servicio y la lista de ítems que envió la pantalla: `[{"descripcion": "Medir voltaje", "obligatorio": true}, ...]`.
- `limpios = [(..., ...) for i in items]` — **comprensión de lista**: por cada ítem arma una pareja (descripción sin espacios y recortada a 255 caracteres, obligatorio como verdadero/falso).
- `limpios = [i for i in limpios if i[0]]` — descarta los ítems con descripción vacía.
- `if not limpios: raise ValidationError(...)` — una plantilla sin ítems no tiene sentido.
- `with transaction.atomic():` — todo lo que sigue se guarda junto o nada.
- `plantilla = ... .first() or PlantillaChecklist.objects.create(...)` — usa la plantilla activa del servicio; si no existe, la crea con el mismo nombre del servicio. El `or` usa el segundo valor cuando el primero es `None`.
- `plantilla.items.all().delete()` — borra los ítems viejos de la plantilla.
- `ItemPlantilla.objects.bulk_create(...)` — crea todos los ítems nuevos en **una sola consulta** a la base de datos.
- `for n, (d, o) in enumerate(limpios, start=1)` — `enumerate` numera los ítems desde 1; ese número se guarda como `orden`.
- `return plantilla` — devuelve la plantilla guardada.

> Las tareas ya creadas **no cambian**: al crear una tarea se **copian** los ítems (ver [Tareas](04-tareas.md)), así que
> editar la plantilla después no afecta los trabajos en curso.

### 3.3 `api.py` — consultar los servicios de una empresa

```python
def tipos_de(empresa):
    activas = PlantillaChecklist.objects.filter(activa=True).prefetch_related(
        Prefetch("items", queryset=ItemPlantilla.objects.order_by("orden", "id"))
    )
    return (
        TipoServicio.objects.filter(empresa=empresa, activo=True)
        .annotate(usos=Count("tareas", distinct=True))
        .prefetch_related(Prefetch("plantillas", queryset=activas, to_attr="activas"))
    )
```

- `def tipos_de(empresa):` — devuelve los servicios activos de una empresa con todo lo que la pantalla necesita.
- `activas = PlantillaChecklist.objects.filter(activa=True).prefetch_related(...)` — consulta de plantillas activas que además trae sus ítems ordenados.
- `Prefetch("items", queryset=...)` — "precarga" los ítems en una consulta aparte en vez de una por plantilla (evita el problema de hacer cientos de consultas).
- `TipoServicio.objects.filter(empresa=empresa, activo=True)` — solo servicios de esa empresa y no archivados (regla 5).
- `.annotate(usos=Count("tareas", distinct=True))` — agrega a cada servicio un dato calculado `usos`: cuántas tareas lo usan. La pantalla lo muestra y avisa antes de archivar.
- `.prefetch_related(Prefetch("plantillas", queryset=activas, to_attr="activas"))` — precarga las plantillas activas y las deja en el atributo `tipo.activas` (una lista).

### 3.4 `api.py` — crear (o reactivar) un servicio

```python
class TiposView(APIView):
    permission_classes = [EsAdministrador]

    def get(self, request):
        return Response([tipo_json(t) for t in tipos_de(request.user.empresa)])

    def post(self, request):
        archivado = TipoServicio.objects.filter(
            empresa=request.user.empresa, activo=False, nombre__iexact=(request.data.get("nombre") or "").strip()
        ).first()
        if archivado:
            archivado.activo = True
            archivado.save(update_fields=["activo"])
            return Response(tipo_json(tipos_de(request.user.empresa).get(pk=archivado.pk)), status=201)
        nombre, error = validar_nombre(request.user.empresa, request.data.get("nombre"))
        if error:
            return Response({"detail": [error]}, status=400)
        tipo = TipoServicio.objects.create(empresa=request.user.empresa, nombre=nombre)
        return Response(tipo_json(tipos_de(request.user.empresa).get(pk=tipo.pk)), status=201)
```

- `permission_classes = [EsAdministrador]` — solo administradores configuran servicios.
- `def get(self, request):` — `GET /api/servicios/`: lista los servicios de su empresa, convertidos a JSON con `tipo_json`.
- `def post(self, request):` — `POST /api/servicios/`: crear un servicio nuevo.
- `archivado = TipoServicio.objects.filter(..., activo=False, nombre__iexact=...).first()` — busca si ya existe un servicio **archivado** con ese nombre (sin distinguir mayúsculas).
- `if archivado:` — como el nombre debe ser único por empresa, no se puede crear otro igual…
- `archivado.activo = True` / `save(...)` — …así que se **reactiva** el archivado, con su plantilla de antes.
- `return Response(..., status=201)` — 201 = "creado".
- `nombre, error = validar_nombre(...)` — comprueba que el nombre no esté vacío ni repetido. La función devuelve dos valores (una **tupla**): el nombre limpio o un mensaje de error.
- `if error: return Response({"detail": [error]}, status=400)` — si hay error, responde 400 con el mensaje.
- `tipo = TipoServicio.objects.create(...)` — crea el servicio en la empresa del administrador.

---

## Cómo se conecta con lo demás

- **Tareas** (`tareas/models.py`) tiene `tipo_servicio = ForeignKey(TipoServicio, on_delete=PROTECT)`.
- `tareas/api.py` reutiliza `tipos_de()` y `tipo_json()` en `/api/tareas/opciones/` para llenar el formulario de nueva tarea.
- En el frontend, la pantalla **Servicios y plantillas** (`pages/admin/Servicios.tsx`) usa estas rutas, y el formulario
  de tareas (`pages/admin/TareaForm.tsx`) copia los ítems de la plantilla al elegir un tipo de servicio.

[← Anterior: Cuentas](02-cuentas.md) · [Índice](../EXPLICACION.md) · [Siguiente: Tareas →](04-tareas.md)
