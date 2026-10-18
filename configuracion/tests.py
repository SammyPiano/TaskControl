from django.test import TestCase

from cuentas.models import Empresa, Usuario
from tareas.models import Tarea

from .models import PlantillaChecklist, TipoServicio


class ServiciosApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="A", rnc="101000001")
        cls.otra = Empresa.objects.create(nombre="B", rnc="101000002")
        cls.admin = Usuario.objects.create_user("admin", empresa=cls.empresa, rol=Usuario.Rol.ADMINISTRADOR)
        cls.empleado = Usuario.objects.create_user("emp", empresa=cls.empresa)
        cls.tipo_otra = TipoServicio.objects.create(empresa=cls.otra, nombre="Ajeno")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_solo_admin(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get("/api/servicios/").status_code, 403)
        self.assertEqual(self.client.post("/api/servicios/", {"nombre": "X"}).status_code, 403)

    def test_crear_tipo_y_nombre_unico(self):
        self.client.post("/api/servicios/", {"nombre": "Instalación"}, content_type="application/json")
        self.assertTrue(TipoServicio.objects.filter(empresa=self.empresa, nombre="Instalación").exists())
        r = self.client.post("/api/servicios/", {"nombre": "instalación"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya existe", r.json()["detail"][0])

    def test_lista_solo_su_empresa_y_no_edita_ajeno(self):
        self.assertEqual(self.client.get("/api/servicios/").json(), [])
        r = self.client.patch(f"/api/servicios/{self.tipo_otra.pk}/", {"nombre": "Y"}, content_type="application/json")
        self.assertEqual(r.status_code, 404)
        r = self.client.put(f"/api/servicios/{self.tipo_otra.pk}/plantilla/", {"items": [{"descripcion": "a"}]},
                            content_type="application/json")
        self.assertEqual(r.status_code, 404)

    def test_guardar_plantilla(self):
        tipo = TipoServicio.objects.create(empresa=self.empresa, nombre="Mantenimiento")
        url = f"/api/servicios/{tipo.pk}/plantilla/"
        items = [{"descripcion": "Revisar", "obligatorio": True}, {"descripcion": "Limpiar", "obligatorio": False}]
        r = self.client.put(url, {"items": items}, content_type="application/json")
        self.assertEqual([i["descripcion"] for i in r.json()["plantilla"]["items"]], ["Revisar", "Limpiar"])
        self.client.put(url, {"items": [{"descripcion": "Solo uno"}]}, content_type="application/json")
        plantilla = PlantillaChecklist.objects.get(tipo_servicio=tipo)
        self.assertEqual(list(plantilla.items.values_list("descripcion", "obligatorio")), [("Solo uno", True)])
        r = self.client.put(url, {"items": [{"descripcion": " "}]}, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_no_elimina_tipo_con_tareas(self):
        tipo = TipoServicio.objects.create(empresa=self.empresa, nombre="Usado")
        Tarea.objects.create(
            empresa=self.empresa, tipo_servicio=tipo, asignado_a=self.empleado, creado_por=self.admin, titulo="T"
        )
        self.assertEqual(self.client.delete(f"/api/servicios/{tipo.pk}/").status_code, 400)
        libre = TipoServicio.objects.create(empresa=self.empresa, nombre="Libre")
        self.assertEqual(self.client.delete(f"/api/servicios/{libre.pk}/").status_code, 204)
