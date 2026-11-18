import { Link, useNavigate, useParams } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { fecha, fechaHora, rd } from "@/lib/formato";
import type { ViaticoDetalle as Viatico } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

export default function ViaticoDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { datos: v, errores } = useApi<Viatico>(`viaticos/${id}/`);

  return (
    <>
      <MobileHeader title="Detalle del viático" back={() => navigate("/viaticos")} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <ErrorBox mensajes={errores} />
        {!v && !errores.length && <Cargando filas={3} alto="h-28" />}
        {v && (
          <>
            <div className="mb-3 flex gap-2"><Badge tipo="viatico" estado={v.estado}>{v.estado_display}</Badge></div>
            <h2 className="mb-1 text-xl font-extrabold leading-tight text-slate-900">{v.concepto}</h2>
            <p className="mb-5 text-sm text-slate-500">{v.codigo} · <Link to={`/tareas/${v.tarea.id}`} className="font-semibold text-wine">{v.tarea.codigo}</Link> · {fecha(v.solicitado_en)}</p>

            {/* En escritorio los gastos van a la izquierda y el resumen, avisos y liquidación a la derecha */}
            <div className="viatico-grid">
              <div className="expense-summary">
                <div><p>Aprobado</p><b>{v.monto_aprobado ? rd(v.monto_aprobado) : "Por autorizar"}</b></div>
                <div><p>Anticipo recibido</p><b>{rd(v.anticipo_entregado)}</b></div>
              </div>

              {v.estado === "RECHAZADO" && v.observacion && (
                <div className="error-box mb-4"><Icon name="alert" size={18} /><span>Rechazado: {v.observacion}</span></div>
              )}
              {v.estado === "SOLICITADO" && <div className="info-strip"><Icon name="clock" /><div><b>Solicitud enviada por {rd(v.monto_solicitado)}</b><span>Espera la autorización del administrador.</span></div></div>}

              <section className="content-card">
                <div className="mb-2 flex items-center justify-between"><div className="section-title !mb-0">Gastos registrados</div><span className="text-xs text-slate-400">{v.gastos.length}</span></div>
                {!v.gastos.length && <p className="py-3 text-xs text-slate-400">{v.admite_gastos ? "Aún no registras gastos." : "Sin gastos."}</p>}
                {v.gastos.map((g) => (
                  <div key={g.id} className="gasto-row">
                    <a className="round-icon" href={g.comprobante} target="_blank" rel="noreferrer" aria-label="Ver comprobante"><Icon name="file" size={18} /></a>
                    <div className="min-w-0 flex-1">
                      <b>{g.categoria_display} · {rd(g.monto)}</b>
                      <span>{fecha(g.fecha)}{g.descripcion && ` · ${g.descripcion}`}</span>
                      {g.estado === "RECHAZADO" && g.observacion && <p className="obs">{g.observacion}</p>}
                    </div>
                    <Badge tipo="gasto" estado={g.estado}>{g.estado_display}</Badge>
                  </div>
                ))}
                <div className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3">
                  <div><small>Aprobados</small><b>{rd(v.totales.aprobado)}</b></div>
                  <div><small>Pendientes</small><b>{rd(v.totales.pendiente)}</b></div>
                  <div><small>Rechazados</small><b>{rd(v.totales.rechazado)}</b></div>
                </div>
              </section>

              {v.liquidacion && (
                <div className="liquidacion-card">
                  <b>{v.liquidacion.resultado_display}: {rd(Math.abs(Number(v.liquidacion.saldo)))}</b>
                  Gastos aprobados {rd(v.liquidacion.total_gastos)} − anticipo {rd(v.liquidacion.total_anticipo)}
                  <div className="mt-1 text-xs">Liquidado por {v.liquidacion.liquidado_por} · {fechaHora(v.liquidacion.liquidada_en)}</div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
      {v?.admite_gastos && (
        <div className="mobile-sticky-action"><Link className="primary-button" to={`/viaticos/${id}/gasto`}><Icon name="plus" size={18} />Registrar gasto</Link></div>
      )}
    </>
  );
}
