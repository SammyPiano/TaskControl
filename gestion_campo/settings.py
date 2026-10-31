"""
Configuración de gestion_campo (CampoTrack).

Variables de entorno (también se leen desde un archivo .env en la raíz):
  DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS
  DB_NAME (archivo SQLite, por defecto db.sqlite3)
"""

import os
from pathlib import Path

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


SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-solo-para-desarrollo-cambiar")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "cuentas",
    "configuracion",
    "tareas",
    "entregas",
    "viaticos",
    "historial",
    "reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gestion_campo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gestion_campo.wsgi.application"

# Base de datos: SQLite
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / env("DB_NAME", "db.sqlite3"),
    }
}

AUTH_USER_MODEL = "cuentas.Usuario"
# La interfaz es la SPA de React en /app/
LOGIN_URL = "/app/ingresar"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/app/ingresar"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idioma, zona horaria y formatos (dd/mm/aaaa)
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santo_Domingo"
USE_I18N = True
USE_TZ = True
FORMAT_MODULE_PATH = ["gestion_campo.formats"]

STATIC_URL = "static/"
STATICFILES_DIRS = []

# Build de React (frontend/dist), servido en /static/app/; index.html lo entrega la vista spa en /app/
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DEV_URL = env("FRONTEND_DEV_URL", "http://localhost:5173/app/")
if FRONTEND_DIST.exists():
    STATICFILES_DIRS.append(("app", FRONTEND_DIST))
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / env("MEDIA_ROOT", "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
