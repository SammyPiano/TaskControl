from django.core.exceptions import ImproperlyConfigured


def filtrar_por_usuario(queryset, usuario, campo_empresa="empresa", campo_propietario=None):
    """
    Regla 5: limita el queryset a la empresa del usuario y, si es empleado, a sus propios
    registros mediante `campo_propietario` (p. ej. "asignado_a"). Admite rutas como "tarea__empresa".
    """
    queryset = queryset.filter(**{campo_empresa: usuario.empresa_id})
    if usuario.es_empleado:
        if not campo_propietario:
            raise ImproperlyConfigured("Defina campo_propietario para filtrar registros de empleados.")
        queryset = queryset.filter(**{campo_propietario: usuario.pk})
    return queryset
