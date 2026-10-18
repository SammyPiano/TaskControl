import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from entregas.tests import imagen
from tareas.models import Tarea
from tareas.tests import Base

from .models import Gasto, Liquidacion, Viatico

MEDIA_PRUEBAS = tempfile.mkdtemp()
D = Decimal


@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class ViaticoBase(Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    def solicitar(self, monto="5000", empleado=None):
        empleado = empleado or self.emp
        return Viatico.solicitar(self.crear_tarea(asignado=empleado), empleado, "Combustible", D(monto))

    def autorizado(self, aprobado="5000", anticipo="0", empleado=None):
        viatico = self.solicitar(aprobado, empleado)
        viatico.autorizar(self.admin, D(aprobado), D(anticipo))
        return viatico

    def gasto(self, viatico, monto, estado=None):
        gasto = viatico.registrar_gasto(
            viatico.empleado, imagen(), Gasto.Categoria.COMBUSTIBLE, timezone.localdate(), D(monto)
        )
        if estado == Gasto.Estado.APROBADO:
            gasto.aprobar(self.admin)
        elif estado == Gasto.Estado.RECHAZADO:
            gasto.rechazar(self.admin, "Sin factura válida")
        return gasto


class ApiMixin:
    def accion(self, viatico, accion, usuario=None, **datos):
        self.client.force_login(usuario or self.admin)
        return self.client.post(f"/api/viaticos/{viatico.pk}/{accion}/", datos, content_type="application/json")

    def registrar(self, viatico, **datos):
        self.client.force_login(self.emp)
        return self.client.post(f"/api/viaticos/{viatico.pk}/gastos/", datos)

    def ids(self, **filtros):
        return [v["id"] for v in self.client.get("/api/viaticos/", filtros).json()["resultados"]]


class SolicitudTests(ApiMixin, ViaticoBase):
    def solicitar_api(self, tarea, monto="1500.50"):
        return self.client.post("/api/viaticos/", {"tarea": tarea.pk, "concepto": "Peajes", "monto_solicitado": monto},
                                content_type="application/json")

    def test_empleado_solicita_por_api(self):
        tarea = self.crear_tarea()
        self.client.force_login(self.emp)
        r = self.solicitar_api(tarea)
        viatico = Viatico.objects.get()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["monto_solicitado"], "1500.50")
        self.assertEqual((viatico.empleado, viatico.estado, viatico.monto_solicitado),
                         (self.emp, Viatico.Estado.SOLICITADO, D("1500.50")))

    def test_no_solicita_para_tarea_ajena_o_cerrada(self):
        ajena = self.crear_tarea(asignado=self.emp2)
        cerrada = self.crear_tarea(estado=Tarea.Estado.COMPLETADA)
        self.client.force_login(self.emp)
        for tarea in (ajena, cerrada):
            self.assertEqual(self.solicitar_api(tarea).status_code, 400)
        self.assertEqual(self.solicitar_api(self.crear_tarea(), "0").status_code, 400)
        self.assertFalse(Viatico.objects.exists())
        with self.assertRaises(ValidationError):
            Viatico.solicitar(ajena, self.emp, "X", D("100"))

    def test_admin_no_solicita(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.solicitar_api(self.crear_tarea()).status_code, 403)


class AutorizacionTests(ApiMixin, ViaticoBase):
    """Regla 7: el anticipo no puede superar el monto aprobado."""

    def test_autoriza_con_anticipo(self):
        viatico = self.solicitar("5000")
        r = self.accion(viatico, "autorizar", monto_aprobado="4000", anticipo="3000")
        self.assertEqual(r.json()["estado"], Viatico.Estado.ANTICIPO_ENTREGADO)
        viatico.refresh_from_db()
        self.assertEqual(viatico.estado, Viatico.Estado.ANTICIPO_ENTREGADO)
        self.assertEqual((viatico.monto_aprobado, viatico.anticipo_entregado, viatico.autorizado_por),
                         (D("4000"), D("3000"), self.admin))

    def test_autoriza_sin_anticipo_y_entrega_despues(self):
        viatico = self.autorizado("4000")
        self.assertEqual(viatico.estado, Viatico.Estado.AUTORIZADO)
        with self.assertRaises(ValidationError):
            viatico.entregar_anticipo(self.admin, D("4000.01"))
        viatico.entregar_anticipo(self.admin, D("4000"))
        self.assertEqual((viatico.estado, viatico.anticipo_entregado), (Viatico.Estado.ANTICIPO_ENTREGADO, D("4000")))

    def test_anticipo_mayor_que_aprobado(self):
        viatico = self.solicitar("5000")
        with self.assertRaises(ValidationError):
            viatico.autorizar(self.admin, D("4000"), D("4500"))
        r = self.accion(viatico, "autorizar", monto_aprobado="4000", anticipo="4500")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no puede superar", r.json()["detail"][0])
        viatico.refresh_from_db()
        self.assertEqual(viatico.estado, Viatico.Estado.SOLICITADO)

    def test_restriccion_en_base_de_datos(self):
        viatico = self.autorizado("1000")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Viatico.objects.filter(pk=viatico.pk).update(anticipo_entregado=D("1000.01"))

    def test_rechazo_exige_observacion(self):
        viatico = self.solicitar()
        with self.assertRaises(ValidationError):
            viatico.rechazar(self.admin, "  ")
        self.assertEqual(self.accion(viatico, "rechazar", observacion="").status_code, 400)
        viatico.refresh_from_db()
        self.assertEqual(viatico.estado, Viatico.Estado.SOLICITADO)
        viatico.rechazar(self.admin, "Fuera de presupuesto")
        self.assertEqual((viatico.estado, viatico.observacion), (Viatico.Estado.RECHAZADO, "Fuera de presupuesto"))

    def test_admin_de_otra_empresa_no_autoriza(self):
        viatico = self.solicitar()
        with self.assertRaises(ValidationError):
            viatico.autorizar(self.admin_otra, D("100"))


class GastoTests(ApiMixin, ViaticoBase):
    def test_registra_gasto_por_api_con_comprobante(self):
        viatico = self.autorizado(anticipo="1000")
        r = self.registrar(viatico, categoria="PEAJE", fecha=timezone.localdate().isoformat(), monto="250",
                           descripcion="Autopista", comprobante=imagen(tamano=(3000, 2000)))
        self.assertEqual(r.status_code, 201)
        gasto = viatico.gastos.get()
        self.assertEqual((gasto.estado, gasto.monto), (Gasto.Estado.PENDIENTE, D("250")))
        self.assertEqual(gasto.comprobante.width, 1920)
        viatico.refresh_from_db()
        self.assertEqual(viatico.estado, Viatico.Estado.EN_COMPROBACION)

    def test_gasto_exige_comprobante_y_fecha_no_futura(self):
        viatico = self.autorizado()
        datos = {"categoria": "PEAJE", "fecha": timezone.localdate().isoformat(), "monto": "250"}
        r = self.registrar(viatico, **datos)
        self.assertIn("comprobante", r.json()["detail"][0])
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.registrar(viatico, **{**datos, "fecha": manana, "comprobante": imagen()})
        self.assertIn("futura", r.json()["detail"][0])
        self.assertFalse(Gasto.objects.exists())

    def test_no_registra_gasto_si_no_esta_autorizado(self):
        viatico = self.solicitar()
        with self.assertRaises(ValidationError):
            self.gasto(viatico, "100")

    def test_rechazo_de_gasto_exige_observacion(self):
        viatico = self.autorizado()
        gasto = self.gasto(viatico, "100")
        with self.assertRaises(ValidationError):
            gasto.rechazar(self.admin, "")
        self.client.force_login(self.admin)
        url = f"/api/gastos/{gasto.pk}/rechazar/"
        r = self.client.post(url, {"observacion": ""}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        gasto.refresh_from_db()
        self.assertEqual(gasto.estado, Gasto.Estado.PENDIENTE)
        r = self.client.post(url, {"observacion": "Ilegible"}, content_type="application/json")
        self.assertEqual(r.json()["gastos"][0]["estado"], Gasto.Estado.RECHAZADO)
        gasto.refresh_from_db()
        self.assertEqual((gasto.estado, gasto.observacion, gasto.revisado_por),
                         (Gasto.Estado.RECHAZADO, "Ilegible", self.admin))


class LiquidacionTests(ApiMixin, ViaticoBase):
    """Regla 6: saldo = gastos aprobados − anticipo; no se liquida con gastos pendientes."""

    def liquidar(self, anticipo, gastos):
        viatico = self.autorizado("5000", anticipo)
        for monto, estado in gastos:
            self.gasto(viatico, monto, estado)
        return viatico.liquidar(self.admin)

    def test_reembolso(self):
        liq = self.liquidar("1000", [("800", "APROBADO"), ("700", "APROBADO"), ("900", "RECHAZADO")])
        self.assertEqual((liq.total_gastos, liq.total_anticipo, liq.saldo, liq.resultado),
                         (D("1500"), D("1000"), D("500"), Liquidacion.Resultado.REEMBOLSO))
        self.assertEqual(liq.viatico.estado, Viatico.Estado.LIQUIDADO)

    def test_devolucion(self):
        liq = self.liquidar("2000", [("1200.25", "APROBADO"), ("500", "RECHAZADO")])
        self.assertEqual((liq.saldo, liq.resultado), (D("-799.75"), Liquidacion.Resultado.DEVOLUCION))

    def test_saldado(self):
        liq = self.liquidar("1000", [("400", "APROBADO"), ("600", "APROBADO")])
        self.assertEqual((liq.saldo, liq.resultado), (D("0"), Liquidacion.Resultado.SALDADO))

    def test_anticipo_sin_gastos_se_devuelve(self):
        liq = self.liquidar("1000", [])
        self.assertEqual((liq.saldo, liq.resultado), (D("-1000"), Liquidacion.Resultado.DEVOLUCION))

    def test_no_liquida_con_gastos_pendientes(self):
        viatico = self.autorizado("5000", "1000")
        self.gasto(viatico, "800", "APROBADO")
        self.gasto(viatico, "300")
        with self.assertRaises(ValidationError):
            viatico.liquidar(self.admin)
        r = self.accion(viatico, "liquidar")
        self.assertEqual(r.status_code, 400)
        self.assertIn("pendientes", r.json()["detail"][0])
        self.assertFalse(Liquidacion.objects.exists())
        viatico.refresh_from_db()
        self.assertEqual(viatico.estado, Viatico.Estado.EN_COMPROBACION)

    def test_liquidado_no_admite_gastos_ni_segunda_liquidacion(self):
        liq = self.liquidar("0", [("100", "APROBADO")])
        viatico = liq.viatico
        with self.assertRaises(ValidationError):
            self.gasto(viatico, "50")
        with self.assertRaises(ValidationError):
            viatico.liquidar(self.admin)

    def test_liquidar_por_api(self):
        viatico = self.autorizado("5000", "1000")
        self.gasto(viatico, "1500", "APROBADO")
        self.client.force_login(self.admin)
        previa = self.client.get(f"/api/viaticos/{viatico.pk}/").json()
        self.assertEqual((previa["saldo"], previa["resultado_previsto"]), ("500.00", "Reembolso al empleado"))
        r = self.accion(viatico, "liquidar")
        self.assertEqual(Liquidacion.objects.get(viatico=viatico).saldo, D("500"))
        self.assertEqual(r.json()["liquidacion"]["resultado_display"], "Reembolso al empleado")
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(f"/api/viaticos/{viatico.pk}/").json()["liquidacion"]["saldo"], "500.00")


class AccesoTests(ApiMixin, ViaticoBase):
    """Regla 5: el empleado solo ve lo suyo; el administrador, lo de su empresa."""

    def test_empleado_solo_ve_sus_viaticos(self):
        propio = self.solicitar()
        ajeno = self.solicitar(empleado=self.emp2)
        self.client.force_login(self.emp)
        self.assertEqual(self.ids(), [propio.pk])
        self.assertEqual(self.client.get(f"/api/viaticos/{ajeno.pk}/").status_code, 404)
        self.assertEqual(self.accion(propio, "autorizar", usuario=self.emp, monto_aprobado="1").status_code, 403)

    def test_empleado_no_registra_gasto_en_viatico_ajeno(self):
        ajeno = self.autorizado(empleado=self.emp2)
        r = self.registrar(ajeno, categoria="PEAJE", fecha=timezone.localdate().isoformat(), monto="10",
                           comprobante=imagen())
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Gasto.objects.exists())

    def test_admin_solo_ve_su_empresa(self):
        viatico = self.solicitar()
        self.client.force_login(self.admin_otra)
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.client.get(f"/api/viaticos/{viatico.pk}/").status_code, 404)
        self.assertEqual(self.accion(viatico, "autorizar", usuario=self.admin_otra, monto_aprobado="10").status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.ids(), [viatico.pk])

    def test_comprobante(self):
        gasto = self.gasto(self.autorizado(), "100")
        url = f"/api/gastos/{gasto.pk}/comprobante/"
        for usuario, esperado in ((self.emp, 200), (self.admin, 200), (self.emp2, 404), (self.admin_otra, 404)):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(url).status_code, esperado, usuario)

    def test_filtro_por_estado(self):
        solicitado = self.solicitar()
        autorizado = self.autorizado()
        self.client.force_login(self.admin)
        self.assertEqual(self.ids(estado="AUTORIZADO"), [autorizado.pk])
        self.assertEqual(self.ids(), [autorizado.pk, solicitado.pk])
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(f"/api/viaticos/{autorizado.pk}/").status_code, 200)

    def test_resumen_del_empleado(self):
        v = self.autorizado("3000", "1000")
        self.gasto(v, "400")
        self.gasto(v, "100", "RECHAZADO")
        self.client.force_login(self.emp)
        resumen = self.client.get("/api/viaticos/").json()["resumen"]
        self.assertEqual(resumen, {"disponible": "2600.00", "por_comprobar": "600.00"})
