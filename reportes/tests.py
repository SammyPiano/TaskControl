import csv
from datetime import timedelta
from decimal import Decimal as D
from io import StringIO

from django.utils import timezone

from cuentas.models import Usuario
from historial.tests import Base
from tareas.models import Tarea

from . import servicios
from .exportar import celda_csv


class ReporteBase(Base):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.desde = self.hoy.replace(day=1)

    def fila(self, reporte, nombre):
        return next(f for f in reporte.filas if f[0] == nombre)


class CumplimientoTests(ReporteBase):
    def test_solo_cuenta_completadas_aprobadas(self):
        """Regla 1: una entrega en revisión no cuenta como completada."""
        self.entrega()  # en revisión
        self.entrega(self.crear_tarea(fecha_limite=self.hoy)).aprobar(self.admin)
        tarde = self.crear_tarea(fecha_limite=self.hoy - timedelta(days=3))
        self.entrega(tarde).aprobar(self.admin)
        self.crear_tarea(fecha_limite=self.hoy - timedelta(days=1))  # vencida
        self.crear_tarea(estado=Tarea.Estado.CANCELADA)

        r = servicios.cumplimiento(self.empresa, self.desde, self.hoy)
        # asignadas, completadas, a tiempo, fuera de plazo, pendientes, vencidas, devoluciones, %cumpl., %a tiempo
        self.assertEqual(self.fila(r, "emp")[1:], [4, 2, 1, 1, 2, 1, 0, 50.0, 50.0])
        self.assertEqual(r.total[0], "Total")

    def test_cuenta_devoluciones(self):
        self.entrega().devolver(self.admin, "Repetir")
        self.assertEqual(self.fila(servicios.cumplimiento(self.empresa, self.desde, self.hoy), "emp")[7], 1)

    def test_filtra_periodo_y_empleado(self):
        vieja = self.crear_tarea()
        Tarea.objects.filter(pk=vieja.pk).update(creada_en=timezone.now() - timedelta(days=60))
        self.crear_tarea(asignado=self.emp2)
        self.crear_tarea()
        r = servicios.cumplimiento(self.empresa, self.hoy, self.hoy, self.emp)
        self.assertEqual([f[:2] for f in r.filas], [["emp", 1]])


class PendientesTests(ReporteBase):
    def test_lista_abiertas_con_atraso(self):
        atrasada = self.crear_tarea(fecha_limite=self.hoy - timedelta(days=5))
        self.crear_tarea(fecha_limite=self.hoy + timedelta(days=2))
        self.entrega(self.crear_tarea()).aprobar(self.admin)
        r = servicios.pendientes(self.empresa, self.desde, self.hoy)
        self.assertEqual(len(r.filas), 2)
        self.assertEqual(r.filas[0][6:], [atrasada.fecha_limite, 5])
        self.assertIsNone(r.filas[1][7])


class ViaticosReporteTests(ReporteBase):
    def test_saldos_por_empleado(self):
        """Regla 6: reembolso y devolución según gastos aprobados − anticipo."""
        v1 = self.autorizado("3000", "1000")
        self.gasto(v1, "1500", "APROBADO")
        v1.liquidar(self.admin)  # reembolso 500
        v2 = self.autorizado("2000", "800")
        self.gasto(v2, "300", "APROBADO")
        v2.liquidar(self.admin)  # devolución 500
        v3 = self.autorizado("1000")
        self.gasto(v3, "200")  # pendiente
        self.solicitar().rechazar(self.admin, "No procede")

        r = servicios.viaticos(self.empresa, self.desde, self.hoy)
        self.assertEqual(self.fila(r, "emp")[1:], [
            4, 1, D("11000"), D("6000"), D("1800"), D("1800"), D("200"), D("500"), D("500"),
        ])


class ReportesApiTests(ReporteBase):
    def test_empresa_y_rol(self):
        """Regla 5."""
        self.crear_tarea()
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/reportes/cumplimiento/").status_code, 403)
        self.client.force_login(self.admin_otra)
        self.assertEqual(self.client.get("/api/reportes/cumplimiento/").json()["filas"], [])
        self.client.force_login(self.admin)
        datos = self.client.get("/api/reportes/cumplimiento/").json()
        self.assertEqual(len(datos["filas"]), 1)
        self.assertEqual(datos["resumen"]["completadas"], 0)
        self.assertEqual(sum(t["b"] for t in datos["serie"]), 1)

    def test_empleado_de_otra_empresa_no_es_filtro_valido(self):
        externo = Usuario.objects.create_user("ext", empresa=self.otra)
        self.client.force_login(self.admin)
        r = self.client.get("/api/reportes/pendientes/", {
            "desde": self.desde.isoformat(), "hasta": self.hoy.isoformat(), "empleado": externo.pk,
        })
        self.assertEqual(r.status_code, 400)

    def test_periodo_invertido(self):
        self.client.force_login(self.admin)
        ayer = self.hoy - timedelta(days=1)
        r = self.client.get("/api/reportes/cumplimiento/", {"desde": self.hoy.isoformat(), "hasta": ayer.isoformat()})
        self.assertEqual(r.status_code, 400)
        self.assertIn("no puede ser posterior", r.json()["detail"][0])

    def test_tipo_inexistente(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/api/reportes/otro/").status_code, 404)

    def test_exporta_csv(self):
        v = self.autorizado("1234.5")
        self.client.force_login(self.admin)
        r = self.client.get("/api/reportes/viaticos/", {
            "desde": self.desde.isoformat(), "hasta": self.hoy.isoformat(), "formato": "csv",
        })
        self.assertIn(f"reporte_viaticos_{self.desde:%Y%m%d}_{self.hoy:%Y%m%d}.csv", r["Content-Disposition"])
        filas = list(csv.reader(StringIO(r.content.decode("utf-8-sig"))))
        self.assertEqual(filas[0][:4], ["Empleado", "Solicitudes", "Rechazadas", "Solicitado"])
        self.assertEqual(filas[1][:5], [str(v.empleado), "1", "0", "1234.50", "1234.50"])
        self.assertEqual(filas[-1][0], "Total")

    def test_todas_las_pestanas(self):
        self.entrega(self.crear_tarea(fecha_limite=self.hoy - timedelta(days=2)))
        self.autorizado("1000", "200")
        self.client.force_login(self.admin)
        for tipo in servicios.REPORTES:
            self.assertEqual(self.client.get(f"/api/reportes/{tipo}/").status_code, 200)


class CeldaCsvTests(ReporteBase):
    def test_formato_y_formulas(self):
        self.assertEqual(celda_csv(self.hoy.replace(day=5, month=3)), f"05/03/{self.hoy.year}")
        self.assertEqual(celda_csv("=SUMA(A1)"), "'=SUMA(A1)")
        self.assertEqual(celda_csv(None), "")


class PanelApiTests(ReporteBase):
    def test_indicadores_de_su_empresa(self):
        """Regla 5: el panel solo cuenta datos de la empresa del administrador."""
        self.crear_tarea(fecha_limite=self.hoy - timedelta(days=1))  # vencida
        self.entrega(self.crear_tarea(prioridad=Tarea.Prioridad.URGENTE))  # en revisión
        self.entrega(self.crear_tarea()).aprobar(self.admin)
        v = self.autorizado("1000", "400")
        self.gasto(v, "250", "APROBADO")

        self.client.force_login(self.admin)
        datos = self.client.get("/api/panel/").json()
        k = datos["kpis"]
        self.assertEqual((k["pendientes"], k["vencidas"], k["en_revision"], k["urgentes_en_revision"]), (2, 1, 1, 1))
        self.assertEqual(k["cumplimiento"], 25)  # 1 completada de 4 asignadas (el viático crea su tarea)
        self.assertEqual((k["viaticos_por_liquidar"], k["monto_por_liquidar"]), (1, "1000.00"))
        self.assertEqual((k["gasto_mes"], k["gastos_mes"]), ("250.00", 1))
        self.assertEqual(len(datos["revisiones"]), 1)
        self.assertTrue(datos["revisiones"][0]["urgente"])

        self.client.force_login(self.admin_otra)
        k = self.client.get("/api/panel/").json()["kpis"]
        self.assertEqual((k["pendientes"], k["en_revision"], k["gastos_mes"]), (0, 0, 0))

    def test_empleado_sin_acceso(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get("/api/panel/").status_code, 403)
