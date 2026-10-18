from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion_campo.api import EmpresaActiva, EsAdministrador

from .forms import LoginForm
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="__str__")
    iniciales = serializers.CharField()
    rol_display = serializers.CharField(source="get_rol_display")
    empresa = serializers.SerializerMethodField()
    notificaciones_sin_leer = serializers.SerializerMethodField()
    entregas_en_revision = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "nombre", "first_name", "iniciales", "email", "rol", "rol_display",
            "cargo", "telefono", "zona", "empresa", "notificaciones_sin_leer", "entregas_en_revision",
        ]

    def get_empresa(self, u):
        e = u.empresa
        return {"id": e.pk, "nombre": e.nombre, "rnc": e.rnc} if e else None

    def get_notificaciones_sin_leer(self, u):
        return u.notificaciones.filter(leida=False).count()

    def get_entregas_en_revision(self, u):
        if not u.es_administrador:
            return 0
        from entregas.models import Entrega

        return Entrega.objects.filter(tarea__empresa=u.empresa_id, estado=Entrega.Estado.EN_REVISION).count()


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


class PerfilView(APIView):
    permission_classes = [EmpresaActiva]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


# Administración de usuarios (solo administradores, solo su empresa: regla 5)

class UsuarioAdminSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="__str__", read_only=True)
    iniciales = serializers.CharField(read_only=True)
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    tareas_activas = serializers.IntegerField(read_only=True, default=0)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "first_name", "last_name", "nombre", "iniciales", "email", "rol", "rol_display",
            "cargo", "telefono", "zona", "is_active", "tareas_activas", "password",
        ]
        extra_kwargs = {"first_name": {"required": True, "allow_blank": False}}

    def validate_username(self, valor):
        valor = valor.strip()
        repetido = Usuario.objects.filter(username__iexact=valor).exclude(pk=getattr(self.instance, "pk", None))
        if repetido.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return valor

    def validate_email(self, valor):
        valor = valor.strip()
        if valor and Usuario.objects.filter(email__iexact=valor).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo.")
        return valor

    def validate(self, datos):
        password = datos.get("password")
        if not self.instance and not password:
            raise serializers.ValidationError({"password": "Indique una contraseña inicial."})
        if password:
            try:
                validate_password(password, Usuario(username=datos.get("username", ""), email=datos.get("email", "")))
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
        return datos

    def create(self, datos):
        password = datos.pop("password")
        usuario = Usuario(**datos)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def update(self, usuario, datos):
        password = datos.pop("password", "")
        for campo, valor in datos.items():
            setattr(usuario, campo, valor)
        if password:
            usuario.set_password(password)
        usuario.save()
        return usuario


def usuarios_de(empresa):
    from tareas.models import Tarea

    return (
        Usuario.objects.filter(empresa=empresa)
        .annotate(tareas_activas=Count("tareas_asignadas", filter=Q(tareas_asignadas__estado__in=Tarea.ESTADOS_ABIERTOS)))
        .order_by("first_name", "last_name", "username")
    )


class UsuariosView(APIView):
    permission_classes = [EsAdministrador]

    def get(self, request):
        qs = usuarios_de(request.user.empresa)
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
                | Q(email__icontains=q) | Q(zona__icontains=q)
            )
        if (rol := request.query_params.get("rol")) in Usuario.Rol.values:
            qs = qs.filter(rol=rol)
        if (estado := request.query_params.get("estado")) in ("activo", "inactivo"):
            qs = qs.filter(is_active=estado == "activo")
        return Response(UsuarioAdminSerializer(qs, many=True).data)

    def post(self, request):
        serializer = UsuarioAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save(empresa=request.user.empresa)
        return Response(UsuarioAdminSerializer(usuarios_de(request.user.empresa).get(pk=usuario.pk)).data, status=201)


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
