from django.test import TestCase

from configuracion.models import ItemPlantilla, PlantillaChecklist, TipoServicio
from cuentas.models import Empresa, Usuario

from .models import ItemChecklist, Tarea


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="A", rnc="101000001")
        cls.otra = Empresa.objects.create(nombre="B", rnc="101000002")
        cls.admin = Usuario.objects.create_user("admin", empresa=cls.empresa, rol=Usuario.Rol.ADMINISTRADOR)
        cls.admin_otra = Usuario.objects.create_user("admin_b", empresa=cls.otra, rol=Usuario.Rol.ADMINISTRADOR)
        cls.emp = Usuario.objects.create_user("emp", empresa=cls.empresa)
        cls.emp2 = Usuario.objects.create_user("emp2", empresa=cls.empresa)
        cls.tipo = TipoServicio.objects.create(empresa=cls.empresa, nombre="Instalación")
        cls.plantilla = PlantillaChecklist.objects.create(tipo_servicio=cls.tipo, nombre="Estándar")
        ItemPlantilla.objects.create(plantilla=cls.plantilla, descripcion="Medir", orden=1)
        ItemPlantilla.objects.create(plantilla=cls.plantilla, descripcion="Foto final", orden=2, obligatorio=False)

    def crear_tarea(self, asignado=None, **extra):
        tarea = Tarea.objects.create(
            empresa=self.empresa, tipo_servicio=self.tipo, asignado_a=asignado or self.emp,
            creado_por=self.admin, titulo="T", **extra,
        )
        tarea.copiar_plantilla(self.plantilla)
        return tarea


def ids(respuesta):
    datos = respuesta.json()
    return [t["id"] for t in (datos["results"] if isinstance(datos, dict) else datos)]


class CrearTareaTests(Base):
    def crear(self, **datos):
        return self.client.post("/api/tareas/", {
            "titulo": "Instalar equipo", "tipo_servicio": self.tipo.pk, "asignado_a": self.emp.pk,
            "prioridad": "ALTA", "fecha_limite": "2026-12-31", **datos,
        }, content_type="application/json")

    def test_crear_con_items_editados(self):
        self.client.force_login(self.admin)
        r = self.crear(items=[{"descripcion": "Medir", "obligatorio": True}, {"descripcion": "Foto final", "obligatorio": False}, {"descripcion": "  "}])
        self.assertEqual(r.status_code, 201)
        tarea = Tarea.objects.get(titulo="Instalar equipo")
        self.assertEqual(r.json()["codigo"], tarea.codigo)
        self.assertEqual((tarea.empresa, tarea.creado_por, tarea.estado), (self.empresa, self.admin, Tarea.Estado.PENDIENTE))
        self.assertEqual(list(tarea.items.values_list("descripcion", "obligatorio", "completado")),
                         [("Medir", True, False), ("Foto final", False, False)])

    def test_cambiar_plantilla_no_afecta_tarea(self):
        tarea = self.crear_tarea()
        self.plantilla.items.all().delete()
        self.assertEqual(tarea.items.count(), 2)

    def test_no_asigna_a_empleado_de_otra_empresa_ni_admin(self):
        externo = Usuario.objects.create_user("ext", empresa=self.otra)
        self.client.force_login(self.admin)
        for asignado in (externo, self.admin):
            self.assertEqual(self.crear(asignado_a=asignado.pk).status_code, 400)
        self.assertFalse(Tarea.objects.exists())

    def test_empleado_no_crea(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.crear().status_code, 403)

    def test_editar_y_reasignar(self):
        tarea = self.crear_tarea()
        self.client.force_login(self.admin)
        r = self.client.patch(f"/api/tareas/{tarea.pk}/", {"titulo": "Nuevo", "asignado_a": self.emp2.pk},
                              content_type="application/json")
        self.assertEqual(r.status_code, 200)
        tarea.refresh_from_db()
        self.assertEqual((tarea.titulo, tarea.asignado_a), ("Nuevo", self.emp2))
        Tarea.objects.filter(pk=tarea.pk).update(estado=Tarea.Estado.COMPLETADA)
        r = self.client.patch(f"/api/tareas/{tarea.pk}/", {"titulo": "X"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)


class ListaTareasTests(Base):
    """Regla 5: filtrado por empresa y por propietario."""

    def test_filtros(self):
        t1 = self.crear_tarea(prioridad=Tarea.Prioridad.URGENTE)
        t2 = self.crear_tarea(asignado=self.emp2)
        self.client.force_login(self.admin)
        self.assertEqual(ids(self.client.get("/api/tareas/")), [t2.pk, t1.pk])
        self.assertEqual(ids(self.client.get("/api/tareas/", {"prioridad": "URGENTE"})), [t1.pk])
        self.assertEqual(ids(self.client.get("/api/tareas/", {"empleado": self.emp2.pk})), [t2.pk])
        self.assertEqual(ids(self.client.get("/api/tareas/", {"estado": "COMPLETADA"})), [])
        self.assertEqual(ids(self.client.get("/api/tareas/", {"q": t1.codigo})), [t1.pk])

    def test_admin_de_otra_empresa_no_ve(self):
        tarea = self.crear_tarea()
        self.client.force_login(self.admin_otra)
        self.assertEqual(ids(self.client.get("/api/tareas/")), [])
        self.assertEqual(self.client.get(f"/api/tareas/{tarea.pk}/").status_code, 404)

    def test_empleado_ve_solo_sus_tareas(self):
        propia = self.crear_tarea()
        ajena = self.crear_tarea(asignado=self.emp2)
        self.client.force_login(self.emp)
        self.assertEqual(ids(self.client.get("/api/mis-tareas/")), [propia.pk])
        self.assertEqual(self.client.get(f"/api/tareas/{propia.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/tareas/{ajena.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/tareas/").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/tareas/{propia.pk}/", {}, content_type="application/json").status_code, 403)


class IniciarYMarcarTests(Base):
    def marcar(self, item, completado=True):
        return self.client.post(f"/api/items/{item.pk}/marcar/", {"completado": completado}, content_type="application/json")

    def test_iniciar(self):
        tarea = self.crear_tarea()
        self.client.force_login(self.emp)
        r = self.client.post(f"/api/tareas/{tarea.pk}/iniciar/")
        self.assertEqual(r.json()["estado"], Tarea.Estado.EN_PROCESO)

    def test_marcar_y_desmarcar(self):
        tarea = self.crear_tarea()
        item = tarea.items.first()
        self.client.force_login(self.emp)
        r = self.marcar(item)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["progreso"], {"hechos": 1, "total": 2, "porcentaje": 50})
        self.assertEqual(r.json()["estado"], Tarea.Estado.EN_PROCESO)
        item.refresh_from_db()
        self.assertTrue(item.completado)
        self.assertIsNotNone(item.marcado_en)

        self.marcar(item, False)
        item.refresh_from_db()
        self.assertFalse(item.completado)
        self.assertIsNone(item.marcado_en)

    def test_no_marca_items_ajenos(self):
        item = self.crear_tarea(asignado=self.emp2).items.first()
        self.client.force_login(self.emp)
        self.assertEqual(self.marcar(item).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.marcar(item).status_code, 403)
        self.assertFalse(ItemChecklist.objects.get(pk=item.pk).completado)

    def test_no_marca_si_tarea_cerrada(self):
        item = self.crear_tarea(estado=Tarea.Estado.EN_REVISION).items.first()
        self.client.force_login(self.emp)
        r = self.marcar(item)
        self.assertEqual(r.status_code, 400)
        self.assertIn("checklist", r.json()["detail"][0])
