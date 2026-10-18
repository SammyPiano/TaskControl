from django.test import Client

from tareas.tests import Base

from .models import Empresa, Usuario


class SesionApiTests(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin.set_password("clave-segura-1")
        cls.admin.save()

    def test_login_y_usuario_actual(self):
        r = self.client.post("/api/sesion/", {"username": "admin", "password": "clave-segura-1"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        datos = r.json()["usuario"]
        self.assertEqual((datos["rol"], datos["empresa"]["nombre"]), ("ADMINISTRADOR", "A"))
        self.assertEqual(self.client.get("/api/sesion/").json()["usuario"]["username"], "admin")

    def test_credenciales_invalidas(self):
        r = self.client.post("/api/sesion/", {"username": "admin", "password": "mala"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.json()["detail"])

    def test_empresa_inactiva_no_ingresa(self):
        inactiva = Empresa.objects.create(nombre="C", rnc="101000003", activa=False)
        u = Usuario.objects.create_user("x", password="clave-segura-1", empresa=inactiva)
        r = self.client.post("/api/sesion/", {"username": u.username, "password": "clave-segura-1"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no está activa", r.json()["detail"][0])

    def test_login_exige_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        r = cliente.post("/api/sesion/", {"username": "admin", "password": "clave-segura-1"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        cliente.get("/api/sesion/")
        token = cliente.cookies["csrftoken"].value
        r = cliente.post("/api/sesion/", {"username": "admin", "password": "clave-segura-1"},
                         content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)

    def test_logout(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete("/api/sesion/").status_code, 204)
        self.assertIsNone(self.client.get("/api/sesion/").json()["usuario"])

    def test_sin_empresa_no_tiene_sesion_en_la_api(self):
        u = Usuario.objects.create_user("suelto")
        self.client.force_login(u)
        self.assertIsNone(self.client.get("/api/sesion/").json()["usuario"])
        self.assertEqual(self.client.get("/api/perfil/").status_code, 403)

    def test_anonimo_sin_acceso(self):
        self.assertEqual(self.client.get("/api/perfil/").status_code, 403)

    def test_login_con_correo(self):
        self.admin.email = "laura@empresa.com"
        self.admin.save()
        r = self.client.post("/api/sesion/", {"username": "Laura@Empresa.com", "password": "clave-segura-1"},
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["usuario"]["username"], "admin")


class UsuariosApiTests(Base):
    """Regla 5: el administrador gestiona solo los usuarios de su empresa."""

    def setUp(self):
        self.client.force_login(self.admin)

    def test_lista_solo_su_empresa(self):
        nombres = {u["username"] for u in self.client.get("/api/usuarios/").json()}
        self.assertEqual(nombres, {"admin", "emp", "emp2"})
        self.assertEqual([u["username"] for u in self.client.get("/api/usuarios/", {"rol": "ADMINISTRADOR"}).json()], ["admin"])

    def test_crear_en_su_empresa(self):
        r = self.client.post("/api/usuarios/", {
            "username": "nuevo", "first_name": "Ana", "last_name": "Pérez", "email": "ana@a.com",
            "rol": "EMPLEADO", "zona": "Santiago", "password": "Clave-Muy-Segura-9", "empresa": self.otra.pk,
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        nuevo = Usuario.objects.get(username="nuevo")
        self.assertEqual((nuevo.empresa, nuevo.zona), (self.empresa, "Santiago"))
        self.assertTrue(nuevo.check_password("Clave-Muy-Segura-9"))

    def test_valida_clave_y_duplicados(self):
        r = self.client.post("/api/usuarios/", {"username": "emp", "first_name": "X", "password": "123"},
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("username", r.json())

    def test_desactivar_y_no_tocar_ajenos(self):
        r = self.client.patch(f"/api/usuarios/{self.emp.pk}/", {"is_active": False}, content_type="application/json")
        self.assertFalse(r.json()["is_active"])
        externo = Usuario.objects.create_user("ext", empresa=self.otra)
        r = self.client.patch(f"/api/usuarios/{externo.pk}/", {"is_active": False}, content_type="application/json")
        self.assertEqual(r.status_code, 404)
        r = self.client.patch(f"/api/usuarios/{self.admin.pk}/", {"is_active": False}, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_empleado_sin_acceso(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 403)
