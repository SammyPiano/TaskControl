# 1. Arranque y configuración

[← Volver al índice](../EXPLICACION.md)

Este documento cubre los archivos de la **raíz** del proyecto y la carpeta **`gestion_campo/`**, que es el
"proyecto" de Django: la configuración general, las rutas principales y unas piezas que usan todas las apps.

## Archivos de la raíz

| Archivo | Para qué sirve |
|---|---|
| `manage.py` | Programa de línea de comandos de Django: `migrate`, `runserver`, `test`, `createsuperuser`, `cargar_demo`… |
| `requirements.txt` | Lista de librerías de Python: Django, Pillow y Django REST Framework, con sus versiones permitidas |
| `.env.example` | Plantilla del archivo `.env`, donde va la configuración que cambia según la máquina (clave secreta, modo depuración…) |
| `.env` | (No está en Git) La configuración real de tu máquina. Lo crea `pnpm preparar` copiando `.env.example` |
| `.gitignore` | Archivos que Git ignora: el entorno virtual `.venv/`, la base de datos, `.env`, las fotos subidas (`media/`)… |
| `db.sqlite3` | (No está en Git) La base de datos. Se crea con `migrate` |
| `media/` | (No está en Git) Las fotos de evidencias y comprobantes que suben los usuarios |
| `README.md` | Instrucciones cortas de instalación y uso |
| `CLAUDE.md` | Reglas del proyecto: tecnologías, modelos, reglas de negocio y convenciones |
| `docs/uml/` | Diagramas UML (casos de uso, clases, estados, secuencias…) escritos en PlantUML |
| `.claude/settings.local.json` | Permisos locales de la herramienta Claude Code (no afecta a la app) |

## Archivos de `gestion_campo/`

| Archivo | Para qué sirve |
|---|---|
| `settings.py` | **Configuración** de Django: apps instaladas, base de datos, idioma, zona horaria, seguridad, DRF |
| `urls.py` | **Rutas principales**: `/admin/`, `/api/…` (reparte a cada app) y `/app/…` (la SPA de React) |
| `views.py` | Vista `spa`: entrega el `index.html` de React para cualquier ruta `/app/…` |
| `api.py` | Piezas comunes de la API: **permisos** (`EmpresaActiva`, `EsAdministrador`, `EsEmpleado`), paginación, manejo de errores y helpers |
| `imagenes.py` | Valida y **redimensiona fotos** (JPG/PNG, máximo 10 MB, máximo 1920 px) |
| `formats/es/formats.py` | Formatos de fecha y número en español dominicano (dd/mm/aaaa) |
| `wsgi.py` / `asgi.py` | Puntos de entrada para servidores de producción (los genera Django) |
| `__init__.py` | Marca la carpeta como paquete de Python |

---

## Fragmentos importantes

### 1.1 `manage.py` — la puerta de entrada de Django

```python
def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestion_campo.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. ...") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- `def main():` — define la función principal del programa.
- `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestion_campo.settings")` — le dice a Django dónde está la configuración. `setdefault` solo la pone si nadie la definió antes.
- `try:` / `from django.core.management import execute_from_command_line` — intenta importar Django.
- `except ImportError as exc:` / `raise ImportError(...)` — si Django no está instalado (por ejemplo, olvidaste activar el entorno virtual), muestra un mensaje claro.
- `execute_from_command_line(sys.argv)` — ejecuta el comando que escribiste. `sys.argv` es la lista de palabras del comando: en `python manage.py migrate` es `["manage.py", "migrate"]`.
- `if __name__ == "__main__":` — esta condición solo es verdadera cuando ejecutas el archivo directamente (no cuando otro archivo lo importa).
- `main()` — llama a la función principal.

### 1.2 `settings.py` — leer el archivo `.env`

```python
BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env(ruta):
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


_cargar_env(BASE_DIR / ".env")


def env(clave, defecto=None):
    return os.environ.get(clave, defecto)


def env_bool(clave, defecto=False):
    return env(clave, str(defecto)).lower() in ("1", "true", "yes", "si", "sí")


def env_lista(clave, defecto=""):
    return [v.strip() for v in env(clave, defecto).split(",") if v.strip()]
```

- `BASE_DIR = Path(__file__).resolve().parent.parent` — calcula la carpeta raíz del proyecto. `__file__` es este archivo (`gestion_campo/settings.py`); `.parent` sube a `gestion_campo/` y el segundo `.parent` sube a `TaskControl/`.
- `def _cargar_env(ruta):` — función que lee un archivo `.env`. El guion bajo inicial indica que es de uso interno.
- `if not ruta.exists(): return` — si no hay `.env`, no hace nada (se usarán los valores por defecto).
- `for linea in ruta.read_text(encoding="utf-8").splitlines():` — lee el archivo completo y recorre cada línea.
- `linea = linea.strip()` — quita espacios al principio y al final.
- `if not linea or linea.startswith("#") or "=" not in linea: continue` — salta líneas vacías, comentarios (`#`) y líneas sin `=`.
- `clave, valor = linea.split("=", 1)` — parte la línea en el primer `=`: `DJANGO_DEBUG=True` da `"DJANGO_DEBUG"` y `"True"`.
- `os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))` — guarda el valor como variable de entorno, quitando comillas. `setdefault` respeta una variable que ya exista en el sistema.
- `_cargar_env(BASE_DIR / ".env")` — ejecuta la función con la ruta del `.env` en la raíz.
- `def env(clave, defecto=None): return os.environ.get(clave, defecto)` — atajo para leer una variable con un valor por defecto.
- `def env_bool(...)` — lee una variable como verdadero/falso: acepta `1`, `true`, `yes`, `si` o `sí`.
- `def env_lista(...)` — lee una lista separada por comas: `"localhost,127.0.0.1"` da `["localhost", "127.0.0.1"]`.

### 1.3 `settings.py` — apps, base de datos y DRF

```python
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-solo-para-desarrollo-cambiar")
DEBUG = env_bool("DJANGO_DEBUG", True)

INSTALLED_APPS = [
    "django.contrib.admin",
    ...
    "rest_framework",
    "cuentas",
    "configuracion",
    "tareas",
    "entregas",
    "viaticos",
    "historial",
    "reportes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / env("DB_NAME", "db.sqlite3"),
    }
}

AUTH_USER_MODEL = "cuentas.Usuario"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santo_Domingo"
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["gestion_campo.api.EmpresaActiva"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "gestion_campo.api.Paginacion",
    "EXCEPTION_HANDLER": "gestion_campo.api.manejar_excepcion",
    "COERCE_DECIMAL_TO_STRING": True,
}

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

- `SECRET_KEY = ...` — clave secreta que Django usa para firmar cookies y tokens. En producción debe venir del `.env`; el valor por defecto solo sirve para desarrollo.
- `DEBUG = env_bool("DJANGO_DEBUG", True)` — modo depuración: muestra errores detallados. Debe estar en `False` en producción.
- `INSTALLED_APPS = [...]` — lista de apps activas: primero las de Django (admin, autenticación, sesiones…), luego DRF (`rest_framework`) y por último las siete apps del proyecto. Si una app no está aquí, Django no ve sus modelos.
- `DATABASES = {...}` — configura la base de datos: motor **SQLite** y el archivo `db.sqlite3` en la raíz (o el nombre que diga `DB_NAME`).
- `AUTH_USER_MODEL = "cuentas.Usuario"` — le dice a Django que el usuario del sistema es nuestro modelo `Usuario` (con empresa y rol), no el usuario estándar.
- `LANGUAGE_CODE = "es"` — mensajes de Django en español.
- `TIME_ZONE = "America/Santo_Domingo"` — hora de República Dominicana.
- `USE_TZ = True` — guarda las fechas en UTC en la base de datos y las convierte a la zona local al mostrarlas.
- `REST_FRAMEWORK = {...}` — configuración de la API:
  - `SessionAuthentication` — identifica al usuario por la cookie de sesión de Django (la misma que al iniciar sesión).
  - `DEFAULT_PERMISSION_CLASSES: EmpresaActiva` — **por defecto, toda vista exige** usuario con sesión y empresa activa. Una vista solo es pública si lo dice explícitamente.
  - `JSONRenderer` — las respuestas siempre son JSON.
  - `DEFAULT_PAGINATION_CLASS` — las listas largas se devuelven por páginas de 20.
  - `EXCEPTION_HANDLER` — función propia para convertir errores del modelo en respuestas 400 (ver 1.6).
  - `COERCE_DECIMAL_TO_STRING: True` — los montos se envían como texto (`"1500.00"`), nunca como número decimal inexacto.
- `if not DEBUG:` — en producción…
- `SESSION_COOKIE_SECURE = True` / `CSRF_COOKIE_SECURE = True` — …las cookies solo viajan por HTTPS.

### 1.4 `urls.py` — el mapa de rutas principal

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include([
        path("", include("cuentas.urls_api")),
        path("", include("configuracion.urls_api")),
        path("", include("tareas.urls_api")),
        path("", include("entregas.urls_api")),
        path("", include("viaticos.urls_api")),
        path("", include("historial.urls_api")),
        path("", include("reportes.urls_api")),
    ])),
    re_path(r"^app(?:/.*)?$", spa, name="spa"),
    path("", RedirectView.as_view(url="/app/", permanent=False)),
]
```

- `urlpatterns = [` — lista que Django recorre en orden hasta encontrar la ruta que coincide.
- `path("admin/", admin.site.urls)` — el panel de administración de Django en `/admin/`.
- `path("api/", include([...]))` — todo lo que empieza con `/api/` se busca en los `urls_api.py` de cada app. Por ejemplo, `/api/tareas/` termina en `tareas/urls_api.py`.
- `path("", include("cuentas.urls_api"))` (y las siguientes) — agrega las rutas de cada app sin prefijo extra.
- `re_path(r"^app(?:/.*)?$", spa, name="spa")` — expresión regular: cualquier ruta que empiece con `/app` (por ejemplo `/app/tareas/5`) la atiende la vista `spa`, que devuelve la página de React. React decide qué pantalla mostrar.
- `path("", RedirectView.as_view(url="/app/", permanent=False))` — si entras a `/`, te redirige a `/app/`.

> No hay ruta para `/media/`: las fotos **no se pueden ver con un enlace directo**. Solo se sirven por la API,
> que primero revisa los permisos (ver 1.6, `servir_archivo`).

### 1.5 `views.py` — entregar la página de React

```python
@ensure_csrf_cookie
def spa(request):
    """Entrega el index.html del build de React para cualquier ruta /app/…"""
    index = settings.FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
    if settings.DEBUG:
        return redirect(settings.FRONTEND_DEV_URL)
    return HttpResponse("Frontend no compilado. Ejecute «pnpm build» en frontend/.", status=503)
```

- `@ensure_csrf_cookie` — decorador que garantiza que el navegador reciba la cookie CSRF junto con la página.
- `def spa(request):` — la vista recibe la petición.
- `index = settings.FRONTEND_DIST / "index.html"` — ruta al `index.html` compilado (`frontend/dist/index.html`).
- `if index.exists(): return FileResponse(...)` — si React ya está compilado (`pnpm build`), envía ese archivo.
- `if settings.DEBUG: return redirect(settings.FRONTEND_DEV_URL)` — si no está compilado pero estás desarrollando, te manda al servidor de Vite (`http://localhost:5173/app/`).
- `return HttpResponse(..., status=503)` — en producción sin compilar, responde "servicio no disponible" con una instrucción.

### 1.6 `api.py` — permisos y errores comunes

```python
class EmpresaActiva(permissions.IsAuthenticated):
    """Autenticado y con empresa activa (regla 5); `roles` opcional."""

    roles = ()
    message = "No tiene permiso para esta acción."

    def has_permission(self, request, view):
        usuario = request.user
        return (
            super().has_permission(request, view)
            and usuario.tiene_empresa_activa
            and (not self.roles or usuario.rol in self.roles)
        )


class EsAdministrador(EmpresaActiva):
    roles = (Usuario.Rol.ADMINISTRADOR,)


class EsEmpleado(EmpresaActiva):
    roles = (Usuario.Rol.EMPLEADO,)
```

- `class EmpresaActiva(permissions.IsAuthenticated):` — un permiso de DRF que **hereda** de `IsAuthenticated` (que solo exige haber iniciado sesión) y le agrega condiciones.
- `roles = ()` — tupla vacía: por defecto acepta cualquier rol.
- `message = "..."` — mensaje que verá el usuario si no tiene permiso (respuesta 403).
- `def has_permission(self, request, view):` — DRF llama a este método antes de ejecutar la vista. Si devuelve `False`, responde 403.
- `usuario = request.user` — el usuario que hace la petición.
- `super().has_permission(request, view)` — primera condición: que haya iniciado sesión (lo revisa la clase padre).
- `and usuario.tiene_empresa_activa` — segunda: que tenga una empresa y que esté activa.
- `and (not self.roles or usuario.rol in self.roles)` — tercera: si la clase define roles, el usuario debe tener uno de ellos.
- `class EsAdministrador(EmpresaActiva): roles = (Usuario.Rol.ADMINISTRADOR,)` — igual que la anterior, pero solo para administradores. La coma final hace que sea una tupla de un elemento.
- `class EsEmpleado(EmpresaActiva): roles = (Usuario.Rol.EMPLEADO,)` — solo para empleados.

```python
def manejar_excepcion(exc, context):
    """Los ValidationError de los métodos del modelo llegan a React como 400 con sus mensajes."""
    from rest_framework.views import exception_handler

    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError({"detail": exc.messages})
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(str(exc) or None)
    return exception_handler(exc, context)
```

- `def manejar_excepcion(exc, context):` — DRF llama a esta función cada vez que una vista lanza un error.
- `from rest_framework.views import exception_handler` — se importa aquí adentro (import "tardío") para evitar un ciclo: `rest_framework.views` a su vez carga estos permisos.
- `if isinstance(exc, DjangoValidationError):` — si el error es una validación de Django (las que lanzan los modelos, como "Esta entrega ya fue revisada")…
- `exc = exceptions.ValidationError({"detail": exc.messages})` — …lo convierte en el error equivalente de DRF, que se responde con **400** y `{"detail": ["mensaje"]}`. Sin esto, sería un error 500 (fallo del servidor).
- `elif isinstance(exc, PermissionDenied):` / `exc = exceptions.PermissionDenied(...)` — lo mismo para "permiso denegado" (403).
- `return exception_handler(exc, context)` — deja que DRF arme la respuesta final.

```python
def servir_archivo(archivo):
    """Archivos protegidos (fotos, comprobantes): nunca por /media/ directo."""
    from django.http import FileResponse, Http404

    try:
        return FileResponse(archivo.open("rb"))
    except (FileNotFoundError, ValueError):
        raise Http404("Archivo no encontrado.")


def persona(usuario):
    return {"id": usuario.pk, "nombre": str(usuario), "iniciales": usuario.iniciales} if usuario else None


def monto(valor):
    """Montos como string decimal en JSON (nunca float)."""
    return None if valor is None else f"{valor:.2f}"
```

- `def servir_archivo(archivo):` — envía un archivo guardado (foto o comprobante). Las vistas solo la llaman **después** de comprobar que el usuario puede verlo.
- `return FileResponse(archivo.open("rb"))` — abre el archivo en modo binario (`"rb"`) y lo envía.
- `except (FileNotFoundError, ValueError): raise Http404(...)` — si el archivo no existe en el disco, responde 404.
- `def persona(usuario):` — convierte un usuario en un diccionario corto `{id, nombre, iniciales}`; si no hay usuario, devuelve `None`. Se usa en muchas respuestas.
- `def monto(valor):` — formatea un monto con 2 decimales como texto: `Decimal("1500")` da `"1500.00"`. `None` se queda como `None`.

### 1.7 `imagenes.py` — validar y achicar fotos

```python
TAMANO_MAXIMO = 10 * 1024 * 1024
LADO_MAXIMO = 1920
EXTENSIONES = {"JPEG": "jpg", "PNG": "png"}


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
```

- `TAMANO_MAXIMO = 10 * 1024 * 1024` — 10 MB expresados en bytes.
- `LADO_MAXIMO = 1920` — ninguna foto quedará con un lado mayor de 1920 píxeles.
- `EXTENSIONES = {...}` — formatos permitidos y la extensión de archivo de cada uno.
- `def procesar_imagen(archivo):` — recibe el archivo subido y devuelve uno nuevo, ya revisado y achicado.
- `validar_tamano(archivo)` — si pesa más de 10 MB, lanza un error.
- `archivo.seek(0)` — vuelve al principio del archivo por si alguien ya lo leyó.
- `with Image.open(archivo) as original:` — Pillow abre la imagen; `with` garantiza que se cierre al terminar.
- `formato = original.format` — formato **real** de la imagen (no se fía del nombre del archivo).
- `if formato not in EXTENSIONES: raise ValidationError(...)` — rechaza GIF, WEBP, etc.
- `imagen = ImageOps.exif_transpose(original)` — gira la foto según el dato EXIF de la cámara (si no, las fotos de teléfono pueden salir de lado).
- `imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))` — la achica manteniendo la proporción, para que ningún lado pase de 1920 px. Si ya era más pequeña, no la toca.
- `except (...): raise ValidationError("El archivo no es una imagen válida.")` — si el archivo está dañado o no es una imagen (o es una "bomba" de descompresión), lo rechaza con un mensaje amable.
- `salida = BytesIO()` — un "archivo" en memoria donde se guardará la nueva imagen.
- `if formato == "JPEG":` — para JPG…
- `if imagen.mode not in ("RGB", "L"): imagen = imagen.convert("RGB")` — …convierte a colores RGB si hace falta (JPG no admite transparencia).
- `imagen.save(salida, "JPEG", quality=85, optimize=True)` — guarda con calidad 85 % (buen equilibrio entre peso y nitidez).
- `else: imagen.save(salida, "PNG", optimize=True)` — los PNG se guardan como PNG.
- `return ContentFile(..., name=f"{uuid.uuid4().hex}.{...}")` — devuelve el archivo listo para guardarse, con un **nombre aleatorio** (así nadie adivina nombres de archivos ni se pisan entre sí).

---

## Cómo se conecta con lo demás

- `settings.py` registra todas las apps y apunta a `gestion_campo.api` para los permisos y errores **de toda la API**.
- `urls.py` reparte cada petición `/api/…` al `urls_api.py` de la app correspondiente.
- `api.py` lo importan todas las vistas (`from gestion_campo.api import EsAdministrador, persona, monto…`).
- `imagenes.py` lo usan los formularios de **entregas** (fotos) y **viáticos** (comprobantes), y los modelos usan `validar_tamano`.
- Los scripts de `frontend/scripts/` (ver [documento 9](09-frontend-base.md)) ejecutan `manage.py` con el Python del entorno virtual.

[← Volver al índice](../EXPLICACION.md) · [Siguiente: Cuentas →](02-cuentas.md)
