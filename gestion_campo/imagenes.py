"""Validación y redimensionado de fotos (evidencias, comprobantes)."""

import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

TAMANO_MAXIMO = 10 * 1024 * 1024
LADO_MAXIMO = 1920
EXTENSIONES = {"JPEG": "jpg", "PNG": "png"}


def validar_tamano(archivo):
    if archivo.size > TAMANO_MAXIMO:
        raise ValidationError("La foto supera los 10 MB.")


def procesar_imagen(archivo):
    """Exige JPG/PNG de hasta 10 MB; corrige la orientación EXIF y limita el lado mayor a 1920 px."""
    validar_tamano(archivo)
    try:
        archivo.seek(0)
        with Image.open(archivo) as original:
            formato = original.format
            if formato not in EXTENSIONES:
                raise ValidationError("Solo se permiten fotos JPG o PNG.")
            imagen = ImageOps.exif_transpose(original)
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ValidationError("El archivo no es una imagen válida.")

    salida = BytesIO()
    if formato == "JPEG":
        if imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")
        imagen.save(salida, "JPEG", quality=85, optimize=True)
    else:
        imagen.save(salida, "PNG", optimize=True)
    return ContentFile(salida.getvalue(), name=f"{uuid.uuid4().hex}.{EXTENSIONES[formato]}")
