from django.test import TestCase

from .mixins import filtrar_por_usuario
from .models import Empresa, Usuario


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre="A", rnc="101000001")
        cls.empresa_b = Empresa.objects.create(nombre="B", rnc="101000002")
        cls.admin_a = Usuario.objects.create_user(
            "admin_a", password="clave-segura-1", empresa=cls.empresa_a, rol=Usuario.Rol.ADMINISTRADOR
        )
        cls.emp_a = Usuario.objects.create_user("emp_a", password="clave-segura-1", empresa=cls.empresa_a)
        cls.emp_a2 = Usuario.objects.create_user("emp_a2", password="clave-segura-1", empresa=cls.empresa_a)
        cls.emp_b = Usuario.objects.create_user("emp_b", password="clave-segura-1", empresa=cls.empresa_b)


class RaizTests(Base):
    def test_raiz_y_login_llevan_a_la_spa(self):
        self.assertRedirects(self.client.get("/"), "/app/", fetch_redirect_response=False)


class FiltroEmpresaTests(Base):
    """Regla 5: el empleado ve solo lo suyo; el administrador, solo su empresa."""

    def test_administrador_ve_solo_su_empresa(self):
        qs = filtrar_por_usuario(Usuario.objects.all(), self.admin_a, campo_propietario="pk")
        self.assertQuerySetEqual(qs, [self.admin_a, self.emp_a, self.emp_a2], ordered=False)

    def test_empleado_ve_solo_lo_suyo(self):
        qs = filtrar_por_usuario(Usuario.objects.all(), self.emp_a, campo_propietario="pk")
        self.assertQuerySetEqual(qs, [self.emp_a])


class CargarDemoTests(TestCase):
    def test_carga_una_sola_vez(self):
        import shutil
        from io import StringIO
        import tempfile

        from django.core.management import CommandError, call_command
        from django.test import override_settings

        from tareas.models import Tarea

        carpeta = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=carpeta):
                call_command("cargar_demo", stdout=StringIO())
                empresa = Empresa.objects.get(rnc="131000999")
                estados = set(Tarea.objects.filter(empresa=empresa).values_list("estado", flat=True))
                self.assertTrue({"PENDIENTE", "EN_PROCESO", "EN_REVISION", "DEVUELTA", "COMPLETADA"} <= estados)
                with self.assertRaises(CommandError):
                    call_command("cargar_demo")
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)
