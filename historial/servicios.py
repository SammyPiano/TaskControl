"""
Registro de historial (regla 8) y notificaciones internas.
Llamar desde los métodos de estado de los modelos, dentro de su misma transacción.
"""

from cuentas.models import Usuario

from .models import Historial, Notificacion


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


# Pantallas de la SPA a las que apuntan las notificaciones e historial (React decide la vista según el rol)
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
