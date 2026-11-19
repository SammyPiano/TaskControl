# 7. Historial y notificaciones

[← Volver al índice](../EXPLICACION.md)

La app **`historial`** tiene dos responsabilidades:

- **Historial**: una bitácora de **todo cambio de estado** (regla 8). Quién hizo qué, cuándo y sobre qué tarea o viático.
  El administrador la ve en la pantalla **Historial** y puede exportarla a CSV.
- **Notificaciones**: avisos internos para un usuario ("Nueva tarea asignada", "Su entrega fue aprobada"…) que se
  muestran en la campana.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `Historial` y `Notificacion` |
| `servicios.py` | Funciones que usan las demás apps: `registrar()`, `cambio()`, `notificar()`, `notificar_administradores()`, `rd()` |
| `api.py` | Vistas: listar y marcar notificaciones, y la bitácora con filtros y CSV |
| `urls_api.py` | Las 4 rutas de la API |
| `admin.py` | Panel `/admin/` |
| `migrations/` | `0001_initial` crea las tablas; `0002_enlaces_spa` convierte enlaces viejos a rutas de React |
| `tests.py` | Pruebas: que cada flujo deje su historial, a quién llegan los avisos y quién puede verlos |

---

## Fragmentos importantes

### 7.1 `models.py` — la bitácora

```python
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
        indexes = [
            models.Index(fields=["empresa", "fecha"]),
            models.Index(fields=["entidad", "entidad_id"]),
        ]
```

- `class Historial(models.Model):` — cada fila es un evento. No hay ninguna función que lo modifique o borre: es **inmutable**.
- `class Entidad(...)` — el evento es sobre una **tarea** o un **viático** (los cambios de entregas y gastos se anotan en su tarea o viático "padre").
- `empresa` — de qué empresa es el evento (para la regla 5).
- `usuario` — quién hizo la acción.
- `entidad` + `entidad_id` — sobre qué registro: por ejemplo `("tarea", 7)`. Se guardan como texto y número en lugar de una FK para poder apuntar a dos tablas distintas.
- `accion` — título corto: "Asignada", "Entrega aprobada", "Liquidado"…
- `detalle` — texto largo: "Versión 2. En revisión → Completada."
- `fecha = models.DateTimeField(default=timezone.now)` — cuándo ocurrió.
- `ordering = ["-fecha", "-id"]` — lo más reciente primero.
- `indexes = [...]` — **índices**: hacen rápidas las búsquedas más comunes (por empresa y fecha, y por tarea/viático), como el índice de un libro.

### 7.2 `servicios.py` — las funciones que usan todas las apps

```python
def registrar(usuario, objeto, accion, detalle=""):
    """`objeto`: Tarea o Viático (la raíz del cambio). La empresa se toma del usuario que actúa."""
    return Historial.objects.create(
        empresa_id=usuario.empresa_id,
        usuario=usuario,
        entidad=objeto._meta.model_name,
        entidad_id=objeto.pk,
        accion=accion[:60],
        detalle=detalle,
    )


def cambio(objeto, anterior):
    """Texto «Anterior → Actual» para el campo `estado` de `objeto`."""
    etiquetas = dict(objeto._meta.get_field("estado").flatchoices)
    return f"{etiquetas.get(anterior, anterior)} → {objeto.get_estado_display()}"


RUTAS_SPA = {"tarea": "/app/tareas/{}", "entrega": "/app/entregas/{}", "viatico": "/app/viaticos/{}"}


def ruta_spa(tipo, pk):
    return RUTAS_SPA[tipo].format(pk)


def notificar(usuarios, mensaje, tipo="", pk=None):
    """`tipo`: clave de RUTAS_SPA para el enlace (tarea, entrega, viatico)."""
    if isinstance(usuarios, Usuario):
        usuarios = [usuarios]
    enlace = ruta_spa(tipo, pk) if tipo else ""
    Notificacion.objects.bulk_create(
        Notificacion(usuario=u, mensaje=mensaje[:255], enlace=enlace) for u in usuarios
    )


def notificar_administradores(empresa_id, mensaje, tipo="", pk=None):
    admins = Usuario.objects.filter(empresa_id=empresa_id, rol=Usuario.Rol.ADMINISTRADOR, is_active=True)
    notificar(list(admins), mensaje, tipo, pk)


def rd(monto):
    return f"RD$ {monto:,.2f}"
```

- `def registrar(usuario, objeto, accion, detalle=""):` — crea un evento en la bitácora. La llaman los métodos de los modelos **dentro de su misma transacción**: si la acción falla, el evento tampoco se guarda.
- `empresa_id=usuario.empresa_id` — la empresa se toma del usuario que actúa.
- `entidad=objeto._meta.model_name` — `_meta.model_name` da el nombre del modelo en minúsculas: `"tarea"` o `"viatico"`.
- `entidad_id=objeto.pk` — el número del registro.
- `accion=accion[:60]` — corta a 60 caracteres (el máximo de la columna).
- `def cambio(objeto, anterior):` — arma el texto "Pendiente → En proceso".
- `etiquetas = dict(objeto._meta.get_field("estado").flatchoices)` — obtiene las opciones del campo `estado` como diccionario `{"PENDIENTE": "Pendiente", ...}`.
- `return f"{etiquetas.get(anterior, anterior)} → {objeto.get_estado_display()}"` — etiqueta del estado anterior → etiqueta del estado actual.
- `RUTAS_SPA = {...}` — a qué pantalla de React apunta cada tipo de enlace.
- `def ruta_spa(tipo, pk): return RUTAS_SPA[tipo].format(pk)` — `ruta_spa("tarea", 7)` da `"/app/tareas/7"`. `.format(pk)` reemplaza `{}` por el número.
- `def notificar(usuarios, mensaje, tipo="", pk=None):` — crea notificaciones para uno o varios usuarios.
- `if isinstance(usuarios, Usuario): usuarios = [usuarios]` — si recibió un solo usuario, lo mete en una lista, así el resto del código funciona igual.
- `enlace = ruta_spa(tipo, pk) if tipo else ""` — arma el enlace solo si se indicó a qué apunta.
- `Notificacion.objects.bulk_create(...)` — crea todas las notificaciones en una consulta.
- `def notificar_administradores(...)` — busca los administradores **activos** de la empresa y les notifica a todos.
- `def rd(monto): return f"RD$ {monto:,.2f}"` — formatea dinero para los mensajes: `1500` → `"RD$ 1,500.00"` (`,` separa miles y `.2f` deja 2 decimales).

### 7.3 `api.py` — notificaciones del usuario

```python
class NotificacionesView(ListAPIView):
    """Solo las del usuario actual."""

    permission_classes = [EmpresaActiva]
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        return self.request.user.notificaciones.all()


class LeerNotificacionView(APIView):
    permission_classes = [EmpresaActiva]

    def post(self, request, pk):
        notificacion = get_object_or_404(request.user.notificaciones, pk=pk)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        return Response(NotificacionSerializer(notificacion).data)
```

- `class NotificacionesView(ListAPIView):` — `GET /api/notificaciones/`, con paginación automática (20 por página).
- `serializer_class = NotificacionSerializer` — convierte cada notificación a JSON (`id`, `mensaje`, `enlace`, `leida`, `creada_en`).
- `def get_queryset(self): return self.request.user.notificaciones.all()` — **solo las del usuario** que pregunta. `notificaciones` es el `related_name` de la FK en `Notificacion`.
- `class LeerNotificacionView(APIView):` — `POST /api/notificaciones/<pk>/leer/`.
- `notificacion = get_object_or_404(request.user.notificaciones, pk=pk)` — busca la notificación **entre las suyas**; la de otra persona da 404.
- `if not notificacion.leida: ...` — la marca como leída (si ya lo estaba, no hace nada).
- `return Response(...)` — devuelve la notificación actualizada.

### 7.4 `api.py` — exportar la bitácora a CSV

```python
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get("formato") == "csv":
            filas = (
                (timezone.localtime(h.fecha), str(h.usuario), h.get_entidad_display(), h.entidad_id, h.accion, h.detalle)
                for h in qs.iterator()
            )
            return respuesta_csv("historial", ["Fecha", "Usuario", "Entidad", "ID", "Acción", "Detalle"], filas)
        pagina = self.paginate_queryset(qs)
        ...
```

- `def list(self, request, *args, **kwargs):` — sobrescribe cómo `HistorialView` responde a `GET /api/historial/`.
- `qs = self.get_queryset()` — la bitácora de **su empresa**, ya filtrada por texto, tipo, acción, usuario y fechas (método `get_queryset`, más arriba en el archivo).
- `if request.query_params.get("formato") == "csv":` — si la URL trae `?formato=csv`…
- `filas = (... for h in qs.iterator())` — …arma las filas con un **generador** (paréntesis en vez de corchetes): las produce una por una sin cargar todo en memoria. `qs.iterator()` también lee de la base de datos por partes.
- `timezone.localtime(h.fecha)` — convierte la fecha a la hora de Santo Domingo.
- `return respuesta_csv("historial", [...], filas)` — usa la función de `reportes/exportar.py` para descargar el archivo `historial.csv`.
- `pagina = self.paginate_queryset(qs)` — si no se pidió CSV, responde en JSON por páginas de 30.

---

## Cómo se conecta con lo demás

- **tareas**, **entregas** y **viáticos** importan `registrar`, `cambio`, `notificar` y `notificar_administradores` desde `historial.servicios`
  y los llaman en cada cambio de estado.
- **cuentas** cuenta las notificaciones sin leer para el punto rojo de la campana (`UsuarioSerializer`).
- Usa **reportes** para el CSV (`respuesta_csv`) y el filtro de fechas (`PeriodoMixin`).
- En el frontend: `pages/Notificaciones.tsx` (empleado y administrador) y `pages/admin/Historial.tsx`. Los enlaces
  `/app/...` se convierten en rutas de React con `rutaSpa()` de `lib/navegacion.ts`.

[← Anterior: Viáticos](06-viaticos.md) · [Índice](../EXPLICACION.md) · [Siguiente: Reportes →](08-reportes.md)
