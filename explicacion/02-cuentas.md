# 2. Cuentas: empresas, usuarios y sesión

[← Volver al índice](../EXPLICACION.md)

La app **`cuentas`** define **quién** usa el sistema: las **empresas** y sus **usuarios** (con su rol de
empleado o administrador). También maneja el **inicio y cierre de sesión** y la pantalla de **Usuarios**
del administrador.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `models.py` | Modelos `Empresa` y `Usuario` (usuario con empresa, rol, cargo, teléfono y zona) |
| `api.py` | Vistas: sesión (`/api/sesion/`), perfil (`/api/perfil/`) y administración de usuarios (`/api/usuarios/`) |
| `urls_api.py` | Las 4 rutas de la API de cuentas |
| `forms.py` | `LoginForm`: permite entrar con el **correo** o con el **nombre de usuario** |
| `mixins.py` | `filtrar_por_usuario()`: la función que aplica la **regla 5** en todo el proyecto |
| `admin.py` | Cómo se ven empresas y usuarios en el panel `/admin/` de Django |
| `management/commands/cargar_demo.py` | Comando `python manage.py cargar_demo`: crea una empresa de ejemplo con datos |
| `migrations/` | `0001_initial` crea las tablas; `0002_…` agrega cargo, teléfono y zona al usuario |
| `tests.py`, `test_api.py` | Pruebas del inicio de sesión, permisos y administración de usuarios |

---

## Fragmentos importantes

### 2.1 `models.py` — Empresa y Usuario

```python
class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    rnc = models.CharField("RNC", max_length=11, unique=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
```

- `class Empresa(models.Model):` — un modelo de Django = una tabla en la base de datos. Cada atributo de tipo `models.…Field` es una columna.
- `nombre = models.CharField(max_length=150)` — texto de hasta 150 caracteres.
- `rnc = models.CharField("RNC", max_length=11, unique=True)` — el RNC (número de contribuyente). `"RNC"` es la etiqueta que se muestra; `unique=True` impide dos empresas con el mismo RNC.
- `telefono = models.CharField("teléfono", max_length=20, blank=True)` — `blank=True` significa que puede quedar vacío.
- `activa = models.BooleanField(default=True)` — si la empresa está desactivada, sus usuarios no pueden entrar.
- `class Meta: ordering = ["nombre"]` — por defecto, las empresas se listan en orden alfabético.
- `def __str__(self): return self.nombre` — cómo se muestra una empresa como texto (por ejemplo, en el panel `/admin/`).

```python
class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        EMPLEADO = "EMPLEADO", "Empleado"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.EMPLEADO)
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    zona = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_empleado(self):
        return self.rol == self.Rol.EMPLEADO

    @property
    def iniciales(self):
        partes = [p for p in (self.first_name, self.last_name) if p] or [self.username]
        return "".join(p[0] for p in partes[:2]).upper()

    @property
    def tiene_empresa_activa(self):
        return self.empresa_id is not None and self.empresa.activa
```

- `class Usuario(AbstractUser):` — **hereda** del usuario de Django (`AbstractUser`), que ya trae `username`, `password`, `first_name`, `last_name`, `email`, `is_active`… Aquí solo se agregan campos nuevos.
- `class Rol(models.TextChoices):` — lista cerrada de opciones. Cada opción tiene el valor que se guarda (`"EMPLEADO"`) y la etiqueta que se muestra (`"Empleado"`).
- `empresa = models.ForeignKey(Empresa, ...)` — cada usuario **pertenece a una empresa** (relación de muchos a uno).
  - `on_delete=models.PROTECT` — no se puede borrar una empresa que tenga usuarios (protege los datos).
  - `related_name="usuarios"` — desde una empresa se llega a sus usuarios con `empresa.usuarios.all()`.
  - `null=True, blank=True` — puede quedar vacía (por ejemplo, el superusuario técnico).
- `rol = models.CharField(..., choices=Rol.choices, default=Rol.EMPLEADO)` — el rol; si no se indica, es empleado.
- `cargo`, `telefono`, `zona` — datos de perfil opcionales.
- `def __str__(self): return self.get_full_name() or self.username` — se muestra el nombre completo; si no tiene, el nombre de usuario.
- `@property` — convierte el método en una **propiedad**: se usa sin paréntesis (`usuario.es_administrador`).
- `es_administrador` / `es_empleado` — comparan el rol. Se usan en todo el código para decidir permisos.
- `iniciales`:
  - `partes = [p for p in (self.first_name, self.last_name) if p] or [self.username]` — toma nombre y apellido si existen; si no hay ninguno, usa el nombre de usuario.
  - `return "".join(p[0] for p in partes[:2]).upper()` — primera letra de cada parte, en mayúsculas: "Carlos Martínez" → "CM". Se muestran en los círculos de avatar.
- `tiene_empresa_activa` — verdadero solo si el usuario tiene empresa **y** esa empresa está activa. Lo usa el permiso `EmpresaActiva`.

### 2.2 `mixins.py` — la regla 5 en una sola función

```python
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
```

- `def filtrar_por_usuario(queryset, usuario, campo_empresa="empresa", campo_propietario=None):` — recibe una consulta (por ejemplo "todas las tareas") y la recorta según quién pregunta.
- `queryset = queryset.filter(**{campo_empresa: usuario.empresa_id})` — **siempre** filtra por la empresa del usuario. `**{...}` arma el filtro con un nombre de campo variable: con `campo_empresa="tarea__empresa"` equivale a `.filter(tarea__empresa=5)`. El doble guion bajo `__` significa "seguir la relación" (la empresa **de la tarea**).
- `if usuario.es_empleado:` — si es empleado, además…
- `if not campo_propietario: raise ImproperlyConfigured(...)` — …exige saber qué campo indica el dueño; si el programador lo olvidó, falla enseguida (mejor que mostrar datos de otros).
- `queryset = queryset.filter(**{campo_propietario: usuario.pk})` — …deja solo los registros de ese empleado (por ejemplo, `asignado_a=usuario`).
- `return queryset` — devuelve la consulta recortada. El administrador ve todo lo de su empresa; el empleado, solo lo suyo.

Se usa así en otras apps: `filtrar_por_usuario(Tarea.objects.all(), usuario, campo_propietario="asignado_a")`.

### 2.3 `forms.py` — entrar con correo o usuario

```python
class LoginForm(AuthenticationForm):
    """Acepta el nombre de usuario o el correo electrónico."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "empresa_inactiva": "Su empresa no está activa. Contacte al administrador.",
    }

    def clean(self):
        identificador = (self.cleaned_data.get("username") or "").strip()
        if "@" in identificador:
            usuario = Usuario.objects.filter(email__iexact=identificador).only("username").first()
            if usuario:
                self.cleaned_data["username"] = usuario.username
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser and not user.tiene_empresa_activa:
            raise ValidationError(self.error_messages["empresa_inactiva"], code="empresa_inactiva")
```

- `class LoginForm(AuthenticationForm):` — hereda el formulario de inicio de sesión de Django, que ya comprueba usuario y contraseña.
- `error_messages = {**AuthenticationForm.error_messages, "empresa_inactiva": ...}` — copia los mensajes originales (`**` "desempaca" el diccionario) y agrega uno nuevo.
- `def clean(self):` — Django llama a `clean` para validar el formulario.
- `identificador = (...).strip()` — lo que escribió el usuario en el campo "usuario", sin espacios.
- `if "@" in identificador:` — si parece un correo…
- `usuario = Usuario.objects.filter(email__iexact=identificador).only("username").first()` — …busca al usuario con ese correo. `__iexact` ignora mayúsculas; `.only("username")` trae solo esa columna; `.first()` devuelve el primero o `None`.
- `self.cleaned_data["username"] = usuario.username` — reemplaza el correo por el nombre de usuario real, porque Django autentica por nombre de usuario.
- `return super().clean()` — deja que el formulario original compruebe la contraseña.
- `def confirm_login_allowed(self, user):` — Django la llama después de verificar la contraseña.
- `super().confirm_login_allowed(user)` — revisa lo estándar (por ejemplo, que la cuenta esté activa).
- `if not user.is_superuser and not user.tiene_empresa_activa: raise ValidationError(...)` — si no es superusuario y su empresa no está activa, no lo deja entrar.

### 2.4 `api.py` — la vista de sesión

```python
@method_decorator(ensure_csrf_cookie, name="dispatch")
class SesionView(APIView):
    """GET: usuario actual (o null) y cookie CSRF. POST: iniciar sesión. DELETE: cerrar sesión."""

    permission_classes = [AllowAny]

    def get(self, request):
        get_token(request)
        usuario = request.user if request.user.is_authenticated and request.user.tiene_empresa_activa else None
        return Response({"usuario": UsuarioSerializer(usuario).data if usuario else None})

    @method_decorator(csrf_protect)
    def post(self, request):
        form = LoginForm(request, data=request.data)
        if not form.is_valid():
            errores = form.non_field_errors() or ["Ingrese su correo o usuario y la contraseña."]
            return Response({"detail": list(errores)}, status=400)
        usuario = form.get_user()
        if not usuario.tiene_empresa_activa:
            return Response({"detail": ["Su usuario no tiene una empresa activa asignada."]}, status=403)
        login(request, usuario)
        return Response({"usuario": UsuarioSerializer(usuario).data})

    def delete(self, request):
        logout(request)
        return Response(status=204)
```

- `@method_decorator(ensure_csrf_cookie, name="dispatch")` — aplica `ensure_csrf_cookie` a **todos** los métodos de la clase: cada respuesta deja la cookie CSRF en el navegador, que React necesitará para hacer `POST`.
- `class SesionView(APIView):` — una vista de DRF basada en clase. Cada método HTTP (`get`, `post`, `delete`) es un método de Python.
- `permission_classes = [AllowAny]` — **excepción** a la regla general: esta vista es pública (si no, nadie podría iniciar sesión).
- `def get(self, request):` — React la llama al cargar la app para saber si ya hay sesión.
- `get_token(request)` — fuerza a generar el token CSRF.
- `usuario = request.user if ... else None` — si hay sesión y empresa activa, devuelve el usuario; si no, `None`.
- `return Response({"usuario": ...})` — responde `{"usuario": {...}}` o `{"usuario": null}`.
- `@method_decorator(csrf_protect)` / `def post(self, request):` — iniciar sesión, con protección CSRF obligatoria.
- `form = LoginForm(request, data=request.data)` — arma el formulario con lo que envió React (`username`, `password`).
- `if not form.is_valid(): ... return Response({...}, status=400)` — si falla, responde 400 con los mensajes de error.
- `usuario = form.get_user()` — el usuario autenticado.
- `if not usuario.tiene_empresa_activa: return Response(..., status=403)` — doble seguro: sin empresa activa, no entra.
- `login(request, usuario)` — Django crea la sesión y envía la cookie `sessionid`.
- `return Response({"usuario": UsuarioSerializer(usuario).data})` — devuelve los datos del usuario para que React los guarde.
- `def delete(self, request): logout(request); return Response(status=204)` — cerrar sesión: borra la sesión y responde 204 (sin contenido).

### 2.5 `api.py` — el serializer del usuario

```python
class UsuarioSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="__str__")
    iniciales = serializers.CharField()
    rol_display = serializers.CharField(source="get_rol_display")
    empresa = serializers.SerializerMethodField()
    notificaciones_sin_leer = serializers.SerializerMethodField()
    entregas_en_revision = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre", "first_name", "iniciales", "email", "rol", "rol_display",
                  "cargo", "telefono", "zona", "empresa", "notificaciones_sin_leer", "entregas_en_revision"]

    def get_empresa(self, u):
        e = u.empresa
        return {"id": e.pk, "nombre": e.nombre, "rnc": e.rnc} if e else None

    def get_notificaciones_sin_leer(self, u):
        return u.notificaciones.filter(leida=False).count()
```

- `class UsuarioSerializer(serializers.ModelSerializer):` — un serializer convierte un objeto `Usuario` en un diccionario listo para JSON.
- `nombre = serializers.CharField(source="__str__")` — el campo `nombre` sale de llamar a `str(usuario)`.
- `iniciales = serializers.CharField()` — lee la propiedad `iniciales` del modelo.
- `rol_display = serializers.CharField(source="get_rol_display")` — Django crea `get_rol_display()` para cada campo con `choices`: devuelve la etiqueta ("Empleado").
- `empresa = serializers.SerializerMethodField()` — el valor lo calcula el método `get_empresa`.
- `class Meta: model = Usuario; fields = [...]` — de qué modelo es y qué campos incluir (nunca la contraseña).
- `def get_empresa(self, u):` — devuelve un mini diccionario de la empresa, o `None`.
- `def get_notificaciones_sin_leer(self, u):` — cuenta las notificaciones no leídas; React lo usa para el punto rojo de la campana.
- (`get_entregas_en_revision`, no mostrado) — para administradores, cuenta las entregas pendientes de revisar; se muestra en el menú lateral.

### 2.6 `api.py` — un administrador no puede quitarse permisos a sí mismo

```python
class UsuarioDetalleView(APIView):
    permission_classes = [EsAdministrador]

    def patch(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk, empresa=request.user.empresa)
        if usuario.pk == request.user.pk and (
            request.data.get("is_active") is False or request.data.get("rol", usuario.rol) != usuario.rol
        ):
            return Response({"detail": ["No puede desactivar su propia cuenta ni cambiar su rol."]}, status=400)
        serializer = UsuarioAdminSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UsuarioAdminSerializer(usuarios_de(request.user.empresa).get(pk=pk)).data)
```

- `permission_classes = [EsAdministrador]` — solo administradores.
- `def patch(self, request, pk):` — `PATCH /api/usuarios/<pk>/` modifica parte de un usuario. `pk` es el número de usuario que viene en la URL.
- `usuario = get_object_or_404(Usuario, pk=pk, empresa=request.user.empresa)` — busca el usuario **dentro de la empresa del administrador** (regla 5). Si es de otra empresa, responde 404 como si no existiera.
- `if usuario.pk == request.user.pk and (...)` — si el administrador intenta editarse a sí mismo **y** quiere desactivarse o cambiar su rol…
- `return Response({...}, status=400)` — …lo impide, para que la empresa no se quede sin administrador por accidente.
- `serializer = UsuarioAdminSerializer(usuario, data=request.data, partial=True)` — `partial=True` permite enviar solo algunos campos.
- `serializer.is_valid(raise_exception=True)` — valida (usuario y correo únicos, contraseña segura…). Si falla, responde 400 automáticamente.
- `serializer.save()` — guarda los cambios (y la nueva contraseña cifrada, si se envió).
- `return Response(...)` — devuelve el usuario actualizado con su número de tareas activas.

### 2.7 `cargar_demo.py` — datos de ejemplo

```python
class Command(BaseCommand):
    help = "Carga una empresa de demostración con usuarios, tareas, entregas y viáticos del diseño."

    def handle(self, *args, **opciones):
        if Empresa.objects.filter(rnc=RNC).exists():
            raise CommandError("Los datos de demostración ya están cargados (empresa RNC 131000999).")
        with transaction.atomic():
            self.cargar()
        self.stdout.write(self.style.SUCCESS(
            "Datos de demostración cargados.\n"
            f"  Administradora: laura@stcaribe.com / {CLAVE}\n"
            f"  Empleado:       cmartinez@stcaribe.com / {CLAVE}"
        ))
```

- `class Command(BaseCommand):` — así se crea un comando propio de `manage.py`; el nombre del comando es el nombre del archivo (`cargar_demo`).
- `help = "..."` — texto que aparece en `python manage.py help cargar_demo`.
- `def handle(self, *args, **opciones):` — lo que se ejecuta al correr el comando.
- `if Empresa.objects.filter(rnc=RNC).exists(): raise CommandError(...)` — si ya se cargaron, no los duplica.
- `with transaction.atomic(): self.cargar()` — crea todo dentro de una transacción: si algo falla, no queda nada a medias.
- `self.stdout.write(self.style.SUCCESS(...))` — imprime en verde los usuarios y la contraseña de prueba.

> `self.cargar()` crea las tareas, entregas y viáticos **llamando a los métodos de los modelos** (`Entrega.presentar`,
> `Viatico.autorizar`…), así el historial y las notificaciones de ejemplo quedan iguales que si un usuario real los hubiera hecho.
> Las fotos de ejemplo se dibujan con Pillow en la función `foto()`, sin descargar nada de internet.

---

## Cómo se conecta con lo demás

- **Todas** las apps tienen un campo `empresa` o llegan a una empresa por una relación (`tarea__empresa`).
- `gestion_campo/api.py` usa `usuario.tiene_empresa_activa` y `usuario.rol` para los permisos.
- `filtrar_por_usuario` lo usan **tareas**, **entregas** y **viáticos** para aplicar la regla 5.
- El frontend llama a `/api/sesion/` desde `lib/sesion.tsx` (ver [documento 9](09-frontend-base.md)) y a `/api/usuarios/` desde la pantalla `admin/Usuarios.tsx`.

[← Anterior: Arranque](01-arranque-y-configuracion.md) · [Índice](../EXPLICACION.md) · [Siguiente: Configuración →](03-configuracion.md)
