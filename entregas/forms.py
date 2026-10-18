from django import forms
from django.core.exceptions import ValidationError

from gestion_campo.imagenes import procesar_imagen

MAX_FOTOS = 10


class FotosInput(forms.FileInput):
    allow_multiple_selected = True


class FotosField(forms.Field):
    widget = FotosInput

    def to_python(self, data):
        return [f for f in (data or []) if f]


class EntregaForm(forms.Form):
    """Valida y redimensiona las fotos de una entrega (multipart: fotos[], descripciones[], comentario)."""

    comentario = forms.CharField(required=False)
    fotos = FotosField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descripciones = self.data.getlist("descripciones") if hasattr(self.data, "getlist") else []

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
