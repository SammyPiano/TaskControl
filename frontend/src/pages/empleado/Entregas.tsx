import { Link, useLocation, useNavigate, useParams } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { fechaHora, plural } from "@/lib/formato";
import type { TareaDetalle } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

/** Historial de versiones de la entrega; si fue devuelta, muestra las correcciones pedidas. */
export default function Entregas() {
  const { id } = useParams();
  const navigate = useNavigate();
  const enviada = (useLocation().state as { enviada?: boolean } | null)?.enviada;
  const { datos: tarea, errores } = useApi<TareaDetalle>(`tareas/${id}/`);
  const devuelta = tarea?.estado === "DEVUELTA" ? tarea.entregas.find((e) => e.revision?.decision === "DEVUELTA") : undefined;

  return (
    <>
      <MobileHeader title={tarea?.estado === "DEVUELTA" ? "Entrega devuelta" : "Historial de entregas"} back={() => navigate("/")} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <ErrorBox mensajes={errores} />
        {!tarea && !errores.length && <Cargando filas={3} alto="h-24" />}
        {enviada && <div className="ok-box mb-5"><Icon name="check" size={18} /><span>Entrega enviada a revisión. Te avisaremos cuando el administrador la revise.</span></div>}
        {devuelta?.revision && (
          <div className="warning-banner">
            <div className="round-icon !bg-orange-100 !text-orange-700"><Icon name="alert" /></div>
            <div>
              <div className="mb-1 font-bold text-orange-900">Se requieren correcciones</div>
              <p className="whitespace-pre-line">{devuelta.revision.observaciones}</p>
              <div className="mt-2 text-xs font-semibold text-orange-800">{devuelta.revision.revisor} · {fechaHora(devuelta.revision.revisada_en)}</div>
            </div>
          </div>
        )}
        {tarea && (
          <>
            <Link to={`/tareas/${id}`} className="mb-1 block text-lg font-extrabold text-slate-900">{tarea.titulo}</Link>
            <p className="mb-6 text-xs text-slate-500">Tarea #{tarea.codigo} · {tarea.tipo_servicio}</p>
            <div className="section-title">Historial de versiones</div>
            {!tarea.entregas.length && <div className="rounded-xl border border-dashed border-slate-300 p-7 text-center text-xs text-slate-400">Aún no has presentado entregas.</div>}
            <div className="timeline">
              {tarea.entregas.map((e, i) => (
                <div key={e.id} className={`timeline-item ${i === 0 ? "active" : ""}`}>
                  <span />
                  <div className="content-card">
                    <div className="mb-2 flex items-center justify-between"><b className="text-sm text-slate-800">Versión {e.version}</b><Badge tipo="entrega" estado={e.estado}>{e.estado_display}</Badge></div>
                    <p className="text-xs leading-relaxed text-slate-500">{plural(e.fotos, "fotografía", "fotografías")}{e.comentario && ` · “${e.comentario}”`}</p>
                    {e.revision?.observaciones && e.revision.decision === "DEVUELTA" && i > 0 && <p className="mt-1 text-xs text-orange-800">{e.revision.observaciones}</p>}
                    <div className="mt-2 flex items-center gap-1 text-[11px] text-slate-400"><Icon name="clock" size={13} />{fechaHora(e.presentada_en)}</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      {tarea?.abierta && (
        <div className="mobile-sticky-action">
          <Link className="primary-button" to={tarea.estado === "DEVUELTA" ? `/tareas/${id}/evidencias` : `/tareas/${id}`}>{tarea.estado === "DEVUELTA" ? "Presentar nueva versión" : "Ir a la tarea"}</Link>
        </div>
      )}
    </>
  );
}
