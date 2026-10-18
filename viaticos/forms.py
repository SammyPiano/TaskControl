from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from gestion_campo.imagenes import procesar_imagen

from .models import Gasto


class GastoForm(forms.ModelForm):
    """Gasto con comprobante (multipart). La foto se valida y redimensiona con Pillow."""

    monto = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    class Meta:
        model = Gasto
        fields = ["categoria", "fecha", "monto", "descripcion", "comprobante"]
        error_messages = {
            "comprobante": {"required": "Adjunte la foto del comprobante."},
            "categoria": {"required": "Elija la categoría.", "invalid_choice": "Elija una categoría válida."},
            "fecha": {"required": "Indique la fecha del gasto."},
        }

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise ValidationError("La fecha no puede ser futura.")
        return fecha

    def clean_comprobante(self):
        return procesar_imagen(self.cleaned_data["comprobante"])
