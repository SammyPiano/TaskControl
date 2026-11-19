# 8. Reportes y panel de indicadores

[← Volver al índice](../EXPLICACION.md)

La app **`reportes`** no tiene modelos propios: **lee** los datos de tareas, entregas y viáticos y calcula
indicadores. Alimenta dos pantallas del administrador:

- **Panel de control**: números del día y del mes (tareas pendientes, vencidas, entregas en revisión, viáticos por liquidar…).
- **Reportes**: tres reportes por período y por empleado (**Cumplimiento**, **Pendientes y retrasos**, **Viáticos**),
  con gráfico y exportación a **CSV** (para abrir en Excel).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `servicios.py` | Los cálculos: clase `Reporte` y funciones `cumplimiento()`, `pendientes()`, `viaticos()` |
| `api.py` | Vistas `PanelView` (`/api/panel/`) y `ReporteView` (`/api/reportes/<tipo>/`), más la serie del gráfico |
| `urls_api.py` | Las 2 rutas |
| `forms.py` | `FiltroReporteForm` (fechas y empleado) y `PeriodoMixin` (filtrar por rango de fechas) |
| `exportar.py` | `respuesta_csv()`: arma el archivo CSV de forma segura |
| `migrations/` | Vacía: la app no tiene tablas |
| `tests.py` | Pruebas de los cálculos, los filtros, los permisos y el CSV |

---

## Fragmentos importantes

### 8.1 `servicios.py` — la clase `Reporte`

```python
TEXTO, ENTERO, MONTO, PORCENTAJE, FECHA = "texto", "entero", "monto", "porcentaje", "fecha"


@dataclass
class Reporte:
    slug: str
    titulo: str
    descripcion: str
    columnas: list  # [(título, tipo)]
    filas: list = field(default_factory=list)
    total: list | None = None

    @property
    def encabezados(self):
        return [c for c, _ in self.columnas]

    def tabla(self):
        return [self._celdas(f) for f in self.filas]

    def filas_csv(self):
        filas = self.filas + ([self.total] if self.total else [])
        return [[csv_valor(v, t) for v, (_, t) in zip(f, self.columnas)] for f in filas]
```

- `TEXTO, ENTERO, ... = "texto", "entero", ...` — asignación múltiple: crea 5 constantes con los tipos de columna.
- `@dataclass` — decorador de Python que crea automáticamente el constructor de la clase a partir de los atributos.
- `slug`, `titulo`, `descripcion` — identificador, título y explicación del reporte.
- `columnas: list` — lista de parejas `(título, tipo)`, por ejemplo `("Asignadas", ENTERO)`.
- `filas: list = field(default_factory=list)` — cada reporte empieza con una lista **nueva** de filas. (Si se pusiera `= []`, todos los reportes compartirían la misma lista: un error clásico).
- `total: list | None = None` — fila de totales, opcional.
- `encabezados` — solo los títulos de las columnas. `for c, _ in` ignora el tipo con `_`.
- `def tabla(self):` — las filas formateadas para mostrar en pantalla ("RD$ 1,500.00", "85.0 %").
- `def filas_csv(self):` — las filas (más el total) con valores "crudos" para el CSV. `zip(f, self.columnas)` empareja cada valor con su columna para saber su tipo.

### 8.2 `servicios.py` — el reporte de cumplimiento

```python
def cumplimiento(empresa, desde, hasta, empleado=None):
    """Tareas creadas en el período (sin canceladas) por empleado."""
    hoy = timezone.localdate()
    tareas = _tareas(empresa, desde, hasta, empleado).exclude(estado=Tarea.Estado.CANCELADA)
    ...
    datos = defaultdict(lambda: defaultdict(int))
    for t in tareas.select_related("asignado_a"):
        d = datos[t.asignado_a]
        d["asignadas"] += 1
        if t.estado == Tarea.Estado.COMPLETADA:
            d["completadas"] += 1
            if t.fecha_limite and timezone.localdate(t.completada_en) > t.fecha_limite:
                d["fuera_plazo"] += 1
            else:
                d["a_tiempo"] += 1
        else:
            d["pendientes"] += 1
            if t.fecha_limite and t.fecha_limite < hoy:
                d["vencidas"] += 1
```

- `def cumplimiento(empresa, desde, hasta, empleado=None):` — calcula, por empleado, cuántas tareas tenía y cómo le fue.
- `hoy = timezone.localdate()` — fecha de hoy en Santo Domingo.
- `tareas = _tareas(...).exclude(estado=CANCELADA)` — tareas de la empresa creadas en el período (y del empleado, si se eligió uno), sin las canceladas.
- `datos = defaultdict(lambda: defaultdict(int))` — un diccionario de diccionarios que **se crea solo**: `datos[empleado]["asignadas"]` empieza en 0 sin tener que inicializarlo.
- `for t in tareas.select_related("asignado_a"):` — recorre cada tarea (con su empleado precargado).
- `d = datos[t.asignado_a]` — los contadores de ese empleado.
- `d["asignadas"] += 1` — suma una tarea asignada.
- `if t.estado == Tarea.Estado.COMPLETADA:` — si está completada…
  - `if t.fecha_limite and timezone.localdate(t.completada_en) > t.fecha_limite:` — …y se completó **después** de la fecha límite → fuera de plazo;
  - `else: d["a_tiempo"] += 1` — si no, a tiempo.
- `else:` — si no está completada…
  - `d["pendientes"] += 1` — …cuenta como pendiente;
  - `if t.fecha_limite and t.fecha_limite < hoy: d["vencidas"] += 1` — …y si ya pasó la fecha, como vencida.

Al final (no mostrado), la función arma una fila por empleado con estos números más dos porcentajes:
**% cumplimiento** = completadas ÷ asignadas y **% a tiempo** = a tiempo ÷ completadas, y una fila **Total**.

### 8.3 `forms.py` — filtrar por período sin errores de zona horaria

```python
def limites(desde, hasta):
    """Rango [desde 00:00, hasta+1 00:00) en la zona local."""
    inicio = timezone.make_aware(datetime.combine(desde, time.min)) if desde else None
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min)) if hasta else None
    return inicio, fin


class PeriodoMixin:
    @staticmethod
    def filtrar_periodo(queryset, campo, desde, hasta):
        inicio, fin = limites(desde, hasta)
        if inicio:
            queryset = queryset.filter(**{f"{campo}__gte": inicio})
        if fin:
            queryset = queryset.filter(**{f"{campo}__lt": fin})
        return queryset
```

- `def limites(desde, hasta):` — convierte dos fechas (días) en dos momentos exactos (fecha y hora).
- `datetime.combine(desde, time.min)` — el día `desde` a las 00:00.
- `timezone.make_aware(...)` — le pone la zona horaria de Santo Domingo (si no, Django no sabría qué medianoche es).
- `hasta + timedelta(days=1)` — el día **siguiente** a `hasta`, a las 00:00. Así se incluye todo el último día, hasta las 23:59:59.
- `class PeriodoMixin:` — un **mixin**: una clase pensada para "mezclarse" con otras y prestarles métodos.
- `def filtrar_periodo(queryset, campo, desde, hasta):` — filtra cualquier consulta por cualquier campo de fecha.
- `queryset.filter(**{f"{campo}__gte": inicio})` — `__gte` = "mayor o igual que". Con `campo="creada_en"` queda `filter(creada_en__gte=inicio)`.
- `queryset.filter(**{f"{campo}__lt": fin})` — `__lt` = "menor que" (estrictamente), para no incluir el día siguiente.

### 8.4 `exportar.py` — CSV seguro para Excel

```python
PELIGROSOS = ("=", "+", "-", "@", "\t", "\r")


def celda_csv(valor):
    """Fechas en dd/mm/aaaa y protección contra inyección de fórmulas en texto libre."""
    if valor is None:
        return ""
    if hasattr(valor, "strftime"):
        formato = "SHORT_DATETIME_FORMAT" if hasattr(valor, "hour") else "SHORT_DATE_FORMAT"
        return formats.date_format(valor, formato)
    if isinstance(valor, str) and valor.startswith(PELIGROSOS):
        return "'" + valor
    return valor


def respuesta_csv(nombre, encabezados, filas):
    """CSV en UTF-8 con BOM para que Excel respete los acentos."""
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}.csv"'
    respuesta.write("﻿")
    escritor = csv.writer(respuesta)
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow([celda_csv(v) for v in fila])
    return respuesta
```

- `PELIGROSOS = (...)` — caracteres con los que Excel interpreta una celda como **fórmula**.
- `def celda_csv(valor):` — prepara cada valor antes de escribirlo.
- `if valor is None: return ""` — vacío en lugar de "None".
- `if hasattr(valor, "strftime"):` — si es una fecha (tiene el método `strftime`)…
- `formato = ... if hasattr(valor, "hour") else ...` — …con hora usa dd/mm/aaaa hh:mm; sin hora, dd/mm/aaaa.
- `if isinstance(valor, str) and valor.startswith(PELIGROSOS): return "'" + valor` — **seguridad**: si un usuario escribió en una observación algo como `=HIPERVINCULO(...)`, se le antepone un apóstrofo para que Excel lo muestre como texto y no lo ejecute (se llama *inyección de fórmulas CSV*).
- `def respuesta_csv(nombre, encabezados, filas):` — crea la respuesta descargable.
- `content_type="text/csv; charset=utf-8"` — le dice al navegador que es un CSV.
- `respuesta["Content-Disposition"] = f'attachment; filename="{nombre}.csv"'` — que lo **descargue** con ese nombre en vez de mostrarlo.
- `respuesta.write("﻿")` — escribe el **BOM** (un carácter invisible al inicio) para que Excel lea bien las tildes y la ñ. En el archivo real el carácter está escrito tal cual y no se ve; aquí se muestra con su código `﻿`.
- `escritor = csv.writer(respuesta)` — el módulo `csv` de Python escribe filas con comas y comillas donde haga falta.
- `escritor.writerow(encabezados)` — primera fila: los títulos.
- `for fila in filas: escritor.writerow([celda_csv(v) for v in fila])` — cada fila, con cada celda preparada.

### 8.5 `api.py` — la vista de reportes

```python
class ReporteView(APIView):
    permission_classes = [EsAdministrador]

    def get(self, request, tipo):
        if tipo not in servicios.REPORTES:
            raise Http404
        empresa = request.user.empresa
        form = FiltroReporteForm(request.query_params, empresa=empresa)
        if not form.is_valid():
            return Response({"detail": [...]}, status=400)
        d = form.cleaned_data
        reporte = servicios.REPORTES[tipo][1](empresa, **d)

        if request.query_params.get("formato") == "csv":
            nombre = f"reporte_{tipo}_{d['desde']:%Y%m%d}_{d['hasta']:%Y%m%d}"
            return respuesta_csv(nombre, reporte.encabezados, reporte.filas_csv())
        ...
```

- `def get(self, request, tipo):` — `GET /api/reportes/cumplimiento/`, `/pendientes/` o `/viaticos/`. `tipo` viene de la URL.
- `if tipo not in servicios.REPORTES: raise Http404` — un tipo desconocido da 404.
- `empresa = request.user.empresa` — **siempre** la empresa del administrador (regla 5).
- `form = FiltroReporteForm(request.query_params, empresa=empresa)` — valida `desde`, `hasta` y `empleado` de la URL. Si no vienen, usa el mes en curso. Solo acepta empleados de su empresa.
- `if not form.is_valid(): return Response(..., status=400)` — por ejemplo, si `desde` es posterior a `hasta`.
- `d = form.cleaned_data` — diccionario con `desde`, `hasta` y `empleado` ya validados.
- `reporte = servicios.REPORTES[tipo][1](empresa, **d)` — busca la función del reporte en el diccionario `REPORTES` (posición `[1]` de la tupla) y la llama. `**d` pasa el diccionario como argumentos con nombre.
- `if ... == "csv":` — si se pidió CSV…
- `nombre = f"reporte_{tipo}_{d['desde']:%Y%m%d}_..."` — …arma un nombre como `reporte_cumplimiento_20261101_20261118`.
- `return respuesta_csv(...)` — …y lo devuelve como descarga.
- (resto) — si no, responde JSON con las filas, el total, un resumen y la **serie** para el gráfico de barras (función `serie()`, que divide el período en hasta 8 tramos).

---

## Cómo se conecta con lo demás

- **Lee** modelos de **tareas**, **entregas** y **viáticos**; no escribe nada.
- Usa `empleados_de()` de `tareas/api.py` para la lista de empleados del filtro.
- `historial/api.py` reutiliza `respuesta_csv` y `PeriodoMixin`.
- En el frontend: `pages/admin/Panel.tsx` (panel) y `pages/admin/Reportes.tsx` (pestañas, gráfico, tabla y botón "Exportar CSV").

[← Anterior: Historial](07-historial.md) · [Índice](../EXPLICACION.md) · [Siguiente: Frontend base →](09-frontend-base.md)
