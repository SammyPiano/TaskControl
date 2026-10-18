from entregas.models import Entrega
from entregas.tests import imagen
from viaticos.tests import D, ViaticoBase

from .models import Historial, Notificacion


class Base(ViaticoBase):
    def entrega(self, tarea=None):
        tarea = tarea or self.crear_tarea()
        tarea.items.filter(obligatorio=True).update(completado=True)
        return Entrega.presentar(tarea, self.emp, [(imagen(), "")])

    def acciones(self, objeto):
        return list(
            Historial.objects.filter(entidad=objeto._meta.model_name, entidad_id=objeto.pk)
            .order_by("id").values_list("accion", flat=True)
        )


class RegistroAutomaticoTests(Base):
    """Regla 8: todo cambio de estado queda en el historial."""

    def test_flujo_de_tarea(self):
        tarea = self.crear_tarea()
        tarea.items.first().marcar(True)
        entrega = Entrega.presentar(tarea, self.emp, [(imagen(), "")])
        entrega.devolver(self.admin, "Falta foto del medidor")
        Entrega.presentar(tarea, self.emp, [(imagen(), "")]).aprobar(self.admin)

        self.assertEqual(self.acciones(tarea), [
            "Iniciada", "Entrega presentada", "Entrega devuelta", "Entrega presentada", "Entrega aprobada",
        ])
        devuelta = Historial.objects.get(entidad="tarea", accion="Entrega devuelta")
        self.assertEqual((devuelta.usuario, devuelta.empresa), (self.admin, self.empresa))
        self.assertIn("En revisión → Devuelta", devuelta.detalle)
        self.assertIn("Falta foto del medidor", devuelta.detalle)

    def test_flujo_de_viatico(self):
        viatico = self.autorizado("3000", "1000")
        self.gasto(viatico, "800", "APROBADO")
        self.gasto(viatico, "100", "RECHAZADO")
        viatico.liquidar(self.admin)

        self.assertEqual(self.acciones(viatico), [
            "Solicitado", "Autorizado", "Gasto registrado", "Gasto aprobado", "Gasto registrado",
            "Gasto rechazado", "Liquidado",
        ])
        liquidado = Historial.objects.get(entidad="viatico", accion="Liquidado")
        self.assertIn("Devolución a la empresa: RD$ 200.00", liquidado.detalle)

    def test_rechazo_y_anticipo_posterior(self):
        rechazado = self.solicitar()
        rechazado.rechazar(self.admin, "Sin presupuesto")
        viatico = self.autorizado("2000")
        viatico.entregar_anticipo(self.admin, D("500"))
        self.assertEqual(self.acciones(rechazado), ["Solicitado", "Rechazado"])
        self.assertEqual(self.acciones(viatico), ["Solicitado", "Autorizado", "Anticipo entregado"])

    def test_accion_fallida_no_deja_registro(self):
        entrega = self.entrega()
        antes = Historial.objects.count()
        with self.assertRaises(Exception):
            entrega.devolver(self.admin, "  ")
        self.assertEqual(Historial.objects.count(), antes)

    def test_crear_y_reasignar_por_api(self):
        self.client.force_login(self.admin)
        self.client.post("/api/tareas/", {
            "titulo": "Nueva", "tipo_servicio": self.tipo.pk, "asignado_a": self.emp.pk, "prioridad": "MEDIA",
        }, content_type="application/json")
        tarea = self.empresa.tareas.get(titulo="Nueva")
        self.client.patch(f"/api/tareas/{tarea.pk}/", {"asignado_a": self.emp2.pk}, content_type="application/json")
        self.assertEqual(self.acciones(tarea), ["Asignada", "Asignada"])
        self.assertTrue(Notificacion.objects.filter(usuario=self.emp2, enlace__contains=str(tarea.pk)).exists())


class NotificacionTests(Base):
    def test_destinatarios(self):
        entrega = self.entrega()
        self.assertTrue(Notificacion.objects.filter(usuario=self.admin, mensaje__contains="para revisión").exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.admin_otra).exists())
        entrega.devolver(self.admin, "Repetir")
        aviso = Notificacion.objects.filter(usuario=self.emp).latest("id")
        self.assertIn("devuelta: Repetir", aviso.mensaje)
        self.assertEqual(aviso.enlace, f"/app/tareas/{entrega.tarea_id}")
        admin = Notificacion.objects.filter(usuario=self.admin).latest("id")
        self.assertEqual(admin.enlace, f"/app/entregas/{entrega.pk}")


class HistorialApiTests(Base):
    """Regla 5: solo el administrador y solo de su empresa."""

    def test_admin_ve_solo_su_empresa(self):
        viatico = self.solicitar()
        self.client.force_login(self.admin_otra)
        self.assertEqual(self.client.get("/api/historial/").json()["count"], 0)
        self.client.force_login(self.admin)
        datos = self.client.get("/api/historial/", {"entidad": "viatico", "entidad_id": viatico.pk}).json()
        self.assertEqual([h["accion"] for h in datos["results"]], ["Solicitado"])
        self.assertEqual(datos["results"][0]["enlace"], f"/app/viaticos/{viatico.pk}")
        self.assertIn("Solicitado", datos["acciones"])
        self.assertEqual(self.client.get("/api/historial/", {"q": "zzz"}).json()["count"], 0)

    def test_empleado_sin_acceso(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/historial/").status_code, 403)

    def test_exporta_csv(self):
        self.solicitar()
        self.client.force_login(self.admin)
        r = self.client.get("/api/historial/", {"formato": "csv"})
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        contenido = r.content.decode("utf-8-sig")
        self.assertTrue(contenido.startswith("Fecha,Usuario,Entidad,ID,Acción,Detalle"))
        self.assertIn("Solicitado", contenido)


class NotificacionesApiTests(Base):
    def test_lista_solo_propias_y_marca_leidas(self):
        self.solicitar()
        self.client.force_login(self.admin)
        datos = self.client.get("/api/notificaciones/").json()
        self.assertEqual(datos["count"], 1)
        n = datos["results"][0]
        self.assertFalse(n["leida"])
        self.assertTrue(self.client.post(f"/api/notificaciones/{n['id']}/leer/").json()["leida"])
        self.assertEqual(self.client.get("/api/sesion/").json()["usuario"]["notificaciones_sin_leer"], 0)

        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/notificaciones/").json()["count"], 0)
        self.assertEqual(self.client.post(f"/api/notificaciones/{n['id']}/leer/").status_code, 404)

    def test_leer_todas(self):
        self.solicitar()
        self.solicitar()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post("/api/notificaciones/leer-todas/").status_code, 204)
        self.assertFalse(Notificacion.objects.filter(usuario=self.admin, leida=False).exists())
