from datetime import datetime, time, timedelta

from django import forms
from django.utils import timezone

from tareas.api import empleados_de


def limites(desde, hasta):
    """Rango [desde 00:00, hasta+1 00:00) en la zona local; evita __date (CONVERT_TZ en MySQL)."""
    inicio = timezone.make_aware(datetime.combine(desde, time.min)) if desde else None
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min)) if hasta else None
    return inicio, fin


class PeriodoMixin:
    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha inicial no puede ser posterior a la final.")
        return datos

    @staticmethod
    def filtrar_periodo(queryset, campo, desde, hasta):
        inicio, fin = limites(desde, hasta)
        if inicio:
            queryset = queryset.filter(**{f"{campo}__gte": inicio})
        if fin:
            queryset = queryset.filter(**{f"{campo}__lt": fin})
        return queryset


class FiltroReporteForm(PeriodoMixin, forms.Form):
    desde = forms.DateField()
    hasta = forms.DateField()
    empleado = forms.ModelChoiceField(
        queryset=None, required=False, error_messages={"invalid_choice": "Elija un empleado de su empresa."}
    )

    def __init__(self, datos, *, empresa):
        """Sin filtros se usa el mes en curso."""
        if not any(datos.get(c) for c in ("desde", "hasta", "empleado")):
            hoy = timezone.localdate()
            datos = {"desde": hoy.replace(day=1).isoformat(), "hasta": hoy.isoformat()}
        super().__init__(datos)
        self.fields["empleado"].queryset = empleados_de(empresa)
