import shutil
import tempfile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from tareas.models import Tarea
from tareas.tests import Base

from .models import Entrega, Evidencia, Revision

MEDIA_PRUEBAS = tempfile.mkdtemp()


def imagen(nombre="foto.jpg", formato="JPEG", tamano=(800, 600)):
    salida = BytesIO()
    Image.new("RGB", tamano, "green").save(salida, formato)
    tipo = {"JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif"}[formato]
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=tipo)


@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class EntregaBase(Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    def tarea_lista(self, **extra):
        tarea = self.crear_tarea(**extra)
        tarea.items.filter(obligatorio=True).update(completado=True)
        return tarea

    def presentar(self, tarea, fotos=None, **datos):
        self.client.force_login(self.emp)
        return self.client.post(
            f"/api/tareas/{tarea.pk}/entregas/",
            {"comentario": "Listo", "fotos": fotos if fotos is not None else [imagen()], **datos},
        )

    def errores(self, r):
        self.assertEqual(r.status_code, 400)
        return " ".join(r.json()["detail"])

    def entrega_en_revision(self):
        tarea = self.tarea_lista()
        return Entrega.presentar(tarea, self.emp, [(imagen(), "")])

    def revisar(self, entrega, accion, observaciones="", usuario=None):
        self.client.force_login(usuario or self.admin)
        return self.client.post(
            f"/api/entregas/{entrega.pk}/{accion}/", {"observaciones": observaciones}, content_type="application/json"
        )


class SolicitarRevisionTests(EntregaBase):
    """Regla 2: ítems obligatorios marcados y al menos una foto."""

    def test_presenta_y_redimensiona(self):
        tarea = self.tarea_lista()
        r = self.presentar(tarea, [imagen(tamano=(4000, 3000)), imagen("b.png", "PNG")], descripciones=["Frente", ""])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["estado"], Tarea.Estado.EN_REVISION)
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, Tarea.Estado.EN_REVISION)
        entrega = tarea.entregas.get()
        self.assertEqual((entrega.version, entrega.estado, entrega.comentario), (1, Entrega.Estado.EN_REVISION, "Listo"))
        evidencias = list(entrega.evidencias.all())
        self.assertEqual([e.descripcion for e in evidencias], ["Frente", ""])
        with Image.open(evidencias[0].archivo.path) as img:
            self.assertEqual(img.size, (1920, 1440))
        self.assertTrue(evidencias[1].archivo.name.endswith(".png"))

    def test_rechaza_con_obligatorios_pendientes(self):
        tarea = self.crear_tarea()
        self.assertIn("Medir", self.errores(self.presentar(tarea)))
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, Tarea.Estado.PENDIENTE)
        self.assertFalse(Entrega.objects.exists())

    def test_item_opcional_no_bloquea(self):
        tarea = self.tarea_lista()
        self.assertFalse(tarea.items.get(obligatorio=False).completado)
        self.assertEqual(self.presentar(tarea).status_code, 201)

    def test_rechaza_sin_fotos(self):
        tarea = self.tarea_lista()
        self.assertIn("al menos una foto", self.errores(self.presentar(tarea, [])))
        self.assertFalse(Entrega.objects.exists())
        with self.assertRaises(ValidationError):
            Entrega.presentar(tarea, self.emp, [])

    def test_rechaza_formato_no_permitido(self):
        tarea = self.tarea_lista()
        falso = SimpleUploadedFile("x.jpg", b"no es imagen", content_type="image/jpeg")
        for archivo in (imagen("a.gif", "GIF"), falso):
            self.errores(self.presentar(tarea, [archivo]))
        self.assertFalse(Entrega.objects.exists())

    def test_rechaza_foto_mayor_a_10_mb(self):
        grande = SimpleUploadedFile("g.jpg", b"0" * (10 * 1024 * 1024 + 1), content_type="image/jpeg")
        self.assertIn("10 MB", self.errores(self.presentar(self.tarea_lista(), [grande])))

    def test_no_presenta_si_ya_esta_en_revision(self):
        entrega = self.entrega_en_revision()
        self.errores(self.presentar(entrega.tarea))
        self.assertEqual(Entrega.objects.count(), 1)


class AprobarTests(EntregaBase):
    """Regla 1: solo la aprobación de un administrador completa la tarea."""

    def test_presentar_no_completa(self):
        entrega = self.entrega_en_revision()
        self.assertEqual(entrega.tarea.estado, Tarea.Estado.EN_REVISION)
        self.assertIsNone(entrega.tarea.completada_en)

    def test_admin_aprueba(self):
        entrega = self.entrega_en_revision()
        self.assertEqual(self.revisar(entrega, "aprobar").status_code, 200)
        entrega.refresh_from_db()
        tarea = entrega.tarea
        self.assertEqual(entrega.estado, Entrega.Estado.APROBADA)
        self.assertEqual(tarea.estado, Tarea.Estado.COMPLETADA)
        self.assertIsNotNone(tarea.completada_en)
        self.assertEqual(entrega.revision.revisor, self.admin)

    def test_empleado_no_aprueba(self):
        entrega = self.entrega_en_revision()
        self.assertEqual(self.revisar(entrega, "aprobar", usuario=self.emp).status_code, 403)
        with self.assertRaises(ValidationError):
            entrega.aprobar(self.emp)
        self.assertEqual(Tarea.objects.get(pk=entrega.tarea_id).estado, Tarea.Estado.EN_REVISION)

    def test_no_se_revisa_dos_veces(self):
        entrega = self.entrega_en_revision()
        entrega.aprobar(self.admin)
        with self.assertRaises(ValidationError):
            Entrega.objects.get(pk=entrega.pk).devolver(self.admin, "Tarde")
        self.assertEqual(Revision.objects.count(), 1)


class DevolverTests(EntregaBase):
    """Reglas 3 y 4: observación obligatoria y nueva versión sin borrar las anteriores."""

    def test_devolver_exige_observacion(self):
        entrega = self.entrega_en_revision()
        self.assertIn("observación", self.errores(self.revisar(entrega, "devolver", "   ")))
        with self.assertRaises(ValidationError):
            entrega.devolver(self.admin, "")
        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, Entrega.Estado.EN_REVISION)
        self.assertFalse(Revision.objects.exists())

    def test_devolver_y_nueva_version(self):
        entrega = self.entrega_en_revision()
        self.revisar(entrega, "devolver", "Falta foto del medidor")
        tarea = Tarea.objects.get(pk=entrega.tarea_id)
        self.assertEqual(tarea.estado, Tarea.Estado.DEVUELTA)

        self.presentar(tarea, [imagen(), imagen()])
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, Tarea.Estado.EN_REVISION)
        self.assertEqual(
            list(tarea.entregas.values_list("version", "estado")),
            [(2, Entrega.Estado.EN_REVISION), (1, Entrega.Estado.DEVUELTA)],
        )
        self.assertEqual(Evidencia.objects.filter(entrega=entrega).count(), 1)
        self.assertEqual(Evidencia.objects.count(), 3)
        self.assertEqual(Revision.objects.get().observaciones, "Falta foto del medidor")

        versiones = self.client.get(f"/api/tareas/{tarea.pk}/").json()["entregas"]
        self.assertEqual([(v["version"], v["fotos"]) for v in versiones], [(2, 2), (1, 1)])
        self.assertEqual(versiones[1]["revision"]["observaciones"], "Falta foto del medidor")
        self.client.force_login(self.admin)
        detalle = self.client.get(f"/api/entregas/{tarea.entregas.first().pk}/").json()
        self.assertEqual((detalle["version"], len(detalle["evidencias"]), len(detalle["tarea"]["entregas"])), (2, 2, 2))


class AccesoTests(EntregaBase):
    """Regla 5: cada quien ve solo lo suyo / lo de su empresa."""

    def test_bandeja_por_empresa(self):
        entrega = self.entrega_en_revision()
        self.client.force_login(self.admin)
        self.assertEqual([e["id"] for e in self.client.get("/api/entregas/").json()], [entrega.pk])
        self.client.force_login(self.admin_otra)
        self.assertEqual(self.client.get("/api/entregas/").json(), [])
        self.assertEqual(self.client.get(f"/api/entregas/{entrega.pk}/").status_code, 404)
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/entregas/").status_code, 403)

    def test_admin_otra_empresa_no_revisa(self):
        entrega = self.entrega_en_revision()
        self.assertEqual(self.revisar(entrega, "aprobar", usuario=self.admin_otra).status_code, 404)
        with self.assertRaises(ValidationError):
            entrega.aprobar(self.admin_otra)

    def test_empleado_no_presenta_tarea_ajena(self):
        tarea = self.crear_tarea(asignado=self.emp2)
        tarea.items.update(completado=True)
        self.assertEqual(self.presentar(tarea).status_code, 404)
        with self.assertRaises(ValidationError):
            Entrega.presentar(tarea, self.emp, [(imagen(), "")])

    def test_fotos_protegidas(self):
        evidencia = self.entrega_en_revision().evidencias.get()
        url = f"/api/evidencias/{evidencia.pk}/archivo/"
        for usuario, codigo in ((self.emp, 200), (self.admin, 200), (self.emp2, 404), (self.admin_otra, 404)):
            self.client.force_login(usuario)
            r = self.client.get(url)
            self.assertEqual(r.status_code, codigo, usuario)
            if codigo == 200:
                r.close()
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 403)
