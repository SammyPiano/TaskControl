import re

from django.db import migrations

# Enlaces de las pantallas Django eliminadas → rutas de la SPA
PATRONES = [
    (re.compile(r"^/tareas/(?:mis-tareas/)?(\d+)/$"), "/app/tareas/{}"),
    (re.compile(r"^/entregas/(\d+)/$"), "/app/entregas/{}"),
    (re.compile(r"^/viaticos/(?:mis-viaticos/)?(\d+)/$"), "/app/viaticos/{}"),
]


def migrar_enlaces(apps, schema_editor):
    Notificacion = apps.get_model("historial", "Notificacion")
    for n in Notificacion.objects.exclude(enlace="").exclude(enlace__startswith="/app/").only("enlace"):
        for patron, ruta in PATRONES:
            if m := patron.match(n.enlace):
                n.enlace = ruta.format(m.group(1))
                break
        else:
            n.enlace = ""
        n.save(update_fields=["enlace"])


class Migration(migrations.Migration):
    dependencies = [("historial", "0001_initial")]

    operations = [migrations.RunPython(migrar_enlaces, migrations.RunPython.noop)]
