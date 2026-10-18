import csv

from django.http import HttpResponse
from django.utils import formats

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
