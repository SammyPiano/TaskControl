"""
Reportes por empleado y período. Cada función devuelve un `Reporte` que se muestra
como tabla o se exporta a CSV. Siempre filtrados por la empresa (regla 5).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import formats, timezone

from entregas.models import Entrega
from tareas.models import Tarea
from viaticos.models import Gasto, Liquidacion, Viatico

from .forms import PeriodoMixin

CERO = Decimal("0.00")
TEXTO, ENTERO, MONTO, PORCENTAJE, FECHA = "texto", "entero", "monto", "porcentaje", "fecha"
ESTADOS_PENDIENTES = (Tarea.Estado.PENDIENTE, Tarea.Estado.EN_PROCESO, Tarea.Estado.EN_REVISION, Tarea.Estado.DEVUELTA)


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

    def _celdas(self, fila):
        return [{"texto": mostrar(v, t), "numero": t != TEXTO and t != FECHA} for v, (_, t) in zip(fila, self.columnas)]

    def tabla(self):
        return [self._celdas(f) for f in self.filas]

    def tabla_total(self):
        return self._celdas(self.total) if self.total else None

    def filas_csv(self):
        filas = self.filas + ([self.total] if self.total else [])
        return [[csv_valor(v, t) for v, (_, t) in zip(f, self.columnas)] for f in filas]


def mostrar(valor, tipo):
    if valor is None or valor == "":
        return "—"
    if tipo == MONTO:
        return f"RD$ {valor:,.2f}"
    if tipo == PORCENTAJE:
        return f"{valor:.1f} %"
    if tipo == FECHA:
        return formats.date_format(valor, "SHORT_DATE_FORMAT")
    return str(valor)


def csv_valor(valor, tipo):
    if valor is None:
        return ""
    if tipo == MONTO:
        return f"{valor:.2f}"
    if tipo == PORCENTAJE:
        return f"{valor:.1f}"
    return valor


def porcentaje(parte, total):
    return parte * 100 / total if total else None


def _por_periodo(queryset, campo, desde, hasta, campo_empleado, empleado):
    queryset = PeriodoMixin.filtrar_periodo(queryset, campo, desde, hasta)
    return queryset.filter(**{campo_empleado: empleado}) if empleado else queryset


def _tareas(empresa, desde, hasta, empleado):
    return _por_periodo(Tarea.objects.filter(empresa=empresa), "creada_en", desde, hasta, "asignado_a", empleado)


def cumplimiento(empresa, desde, hasta, empleado=None):
    """Tareas creadas en el período (sin canceladas) por empleado."""
    hoy = timezone.localdate()
    tareas = _tareas(empresa, desde, hasta, empleado).exclude(estado=Tarea.Estado.CANCELADA)
    devoluciones = dict(
        Entrega.objects.filter(tarea__in=tareas, estado=Entrega.Estado.DEVUELTA)
        .values_list("tarea__asignado_a").annotate(n=Count("id")).order_by()
    )

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

    claves = ("asignadas", "completadas", "a_tiempo", "fuera_plazo", "pendientes", "vencidas", "devoluciones")

    def fila(nombre, d):
        valores = [d[c] for c in claves]
        return [nombre, *valores,
                porcentaje(d["completadas"], d["asignadas"]), porcentaje(d["a_tiempo"], d["completadas"])]

    reporte = Reporte(
        "cumplimiento", "Cumplimiento",
        "Tareas creadas en el período por empleado. «A tiempo»: completadas antes o en la fecha límite.",
        [("Empleado", TEXTO), ("Asignadas", ENTERO), ("Completadas", ENTERO), ("A tiempo", ENTERO),
         ("Fuera de plazo", ENTERO), ("Pendientes", ENTERO), ("Vencidas", ENTERO), ("Devoluciones", ENTERO),
         ("% Cumplimiento", PORCENTAJE), ("% A tiempo", PORCENTAJE)],
    )
    total = defaultdict(int)
    for usuario in sorted(datos, key=str):
        d = datos[usuario]
        d["devoluciones"] = devoluciones.get(usuario.pk, 0)
        for c in claves:
            total[c] += d[c]
        reporte.filas.append(fila(str(usuario), d))
    if reporte.filas:
        reporte.total = fila("Total", total)
    return reporte


def pendientes(empresa, desde, hasta, empleado=None):
    """Tareas abiertas creadas en el período, de la más atrasada a la más holgada."""
    hoy = timezone.localdate()
    tareas = (
        _tareas(empresa, desde, hasta, empleado)
        .filter(estado__in=ESTADOS_PENDIENTES)
        .select_related("asignado_a", "tipo_servicio")
    )
    tareas = sorted(tareas, key=lambda t: (str(t.asignado_a), t.fecha_limite or hoy.max, t.pk))
    reporte = Reporte(
        "pendientes", "Pendientes",
        "Tareas sin completar creadas en el período. Días de atraso respecto a la fecha límite.",
        [("Empleado", TEXTO), ("Tarea", TEXTO), ("Tipo de servicio", TEXTO), ("Prioridad", TEXTO),
         ("Estado", TEXTO), ("Creada", FECHA), ("Fecha límite", FECHA), ("Días de atraso", ENTERO)],
    )
    for t in tareas:
        atraso = (hoy - t.fecha_limite).days if t.fecha_limite and t.fecha_limite < hoy else None
        reporte.filas.append([
            str(t.asignado_a), t.titulo, str(t.tipo_servicio), t.get_prioridad_display(), t.get_estado_display(),
            timezone.localdate(t.creada_en), t.fecha_limite, atraso,
        ])
    return reporte


def viaticos(empresa, desde, hasta, empleado=None):
    """Viáticos solicitados en el período por empleado. Regla 6: saldo según liquidaciones."""
    qs = _por_periodo(Viatico.objects.filter(tarea__empresa=empresa), "solicitado_en", desde, hasta, "empleado", empleado)

    gastos = defaultdict(dict)
    for emp, estado, suma in (
        Gasto.objects.filter(viatico__in=qs).values_list("viatico__empleado", "estado").annotate(s=Sum("monto")).order_by()
    ):
        gastos[emp][estado] = suma
    liquidado = defaultdict(dict)
    for emp, resultado, suma in (
        Liquidacion.objects.filter(viatico__in=qs).values_list("viatico__empleado", "resultado")
        .annotate(s=Sum("saldo")).order_by()
    ):
        liquidado[emp][resultado] = abs(suma)

    datos = defaultdict(lambda: defaultdict(lambda: CERO))
    nombres = {}
    for v in qs.select_related("empleado"):
        nombres[v.empleado_id] = str(v.empleado)
        d = datos[v.empleado_id]
        d["solicitudes"] += 1
        if v.estado == Viatico.Estado.RECHAZADO:
            d["rechazadas"] += 1
        d["solicitado"] += v.monto_solicitado
        d["aprobado"] += v.monto_aprobado or CERO
        d["anticipo"] += v.anticipo_entregado
    for emp, d in datos.items():
        d["gastos_aprobados"] = gastos[emp].get(Gasto.Estado.APROBADO, CERO)
        d["gastos_pendientes"] = gastos[emp].get(Gasto.Estado.PENDIENTE, CERO)
        d["reembolso"] = liquidado[emp].get(Liquidacion.Resultado.REEMBOLSO, CERO)
        d["devolucion"] = liquidado[emp].get(Liquidacion.Resultado.DEVOLUCION, CERO)

    claves = ("solicitudes", "rechazadas", "solicitado", "aprobado", "anticipo",
              "gastos_aprobados", "gastos_pendientes", "reembolso", "devolucion")
    reporte = Reporte(
        "viaticos", "Viáticos",
        "Viáticos solicitados en el período. Reembolso y devolución corresponden a los ya liquidados.",
        [("Empleado", TEXTO), ("Solicitudes", ENTERO), ("Rechazadas", ENTERO), ("Solicitado", MONTO),
         ("Aprobado", MONTO), ("Anticipos", MONTO), ("Gastos aprobados", MONTO), ("Gastos pendientes", MONTO),
         ("Reembolso al empleado", MONTO), ("Devolución a la empresa", MONTO)],
    )
    total = defaultdict(lambda: CERO)
    for emp in sorted(datos, key=lambda e: nombres[e]):
        d = datos[emp]
        for c in claves:
            total[c] += d[c]
        reporte.filas.append([nombres[emp], *(int(d[c]) if i < 2 else d[c] for i, c in enumerate(claves))])
    if reporte.filas:
        reporte.total = ["Total", *(int(total[c]) if i < 2 else total[c] for i, c in enumerate(claves))]
    return reporte


# slug → (pestaña, generador)
REPORTES = {
    "cumplimiento": ("Cumplimiento", cumplimiento),
    "pendientes": ("Pendientes y retrasos", pendientes),
    "viaticos": ("Viáticos", viaticos),
}
