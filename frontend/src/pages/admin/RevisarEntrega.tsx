import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import { api, mensajesDe } from "@/lib/api";
import { fechaHora, plural, vence } from "@/lib/formato";
import { useSesion } from "@/lib/sesion";
import type { EntregaDetalle } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";
import { criterios } from "@/pages/empleado/TareaDetalle";

export default function RevisarEntrega() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { refrescar } = useSesion();
  const { datos: e, errores: errCarga, recargar } = useApi<EntregaDetalle>(`entregas/${id}/`);
  const [foto, setFoto] = useState(0);
  const [devolviendo, setDevolviendo] = useState(false);
  const [observaciones, setObservaciones] = useState("");
  const [aprobada, setAprobada] = useState(false);
  const [errores, setErrores] = useState<string[]>([]);
  const [ocupado, setOcupado] = useState(false);

  const revisar = async (accion: "aprobar" | "devolver") => {
    setOcupado(true);
    try {
      await api(`entregas/${id}/${accion}/`, { method: "POST", body: { observaciones } });
      refrescar();
      if (accion === "devolver") return navigate("/entregas", { replace: true });
      setAprobada(true);
      setErrores([]);
      recargar();
    } catch (err) {
      setErrores(mensajesDe(err));
    } finally {
      setOcupado(false);
    }
  };

  const t = e?.tarea;
  const anteriores = t?.entregas.filter((v) => v.id !== e?.id) ?? [];
  const actual = e?.evidencias[foto];

  return (
    <>
      <Heading title={t ? `Revisar entrega · ${t.codigo}` : "Revisar entrega"} description={e ? `Versión ${e.version} · ${e.empleado.nombre} · ${fechaHora(e.presentada_en)}` : "Cargando…"}>
        <button className="admin-secondary" onClick={() => navigate(-1)}><Icon name="arrow" size={17} />Volver</button>
      </Heading>
      {aprobada && <div className="success-banner"><Icon name="check" /><div><b>Entrega aprobada correctamente</b><span>La tarea pasó a Completada y el empleado fue notificado.</span></div></div>}
      <ErrorBox mensajes={errCarga} />
      {!e && !errCarga.length && <Cargando filas={3} alto="h-40" />}
      {e && t && (
        <div className="review-layout">
          <section className="admin-card">
            <div className="card-heading mb-4"><div><h2>Evidencias fotográficas</h2><p>{plural(e.evidencias.length, "archivo adjunto", "archivos adjuntos")}</p></div><Badge tipo="entrega" estado={e.estado}>{e.estado_display}</Badge></div>
            {actual ? (
              <div className="photo-viewer">
                <img src={actual.url} alt={actual.descripcion || `Evidencia ${foto + 1}`} />
                <a href={actual.url} target="_blank" rel="noreferrer" aria-label="Abrir foto en tamaño completo" />
                <div><Icon name="search" size={18} />Foto {foto + 1} de {e.evidencias.length}{actual.descripcion && ` · ${actual.descripcion}`}</div>
              </div>
            ) : <div className="photo-viewer vacio">Sin fotos</div>}
            {e.evidencias.length > 1 && (
              <div className="photo-thumbs">
                {e.evidencias.map((ev, i) => <button key={ev.id} className={foto === i ? "active" : ""} onClick={() => setFoto(i)} aria-label={`Ver foto ${i + 1}`}><img src={ev.url} alt="" /></button>)}
              </div>
            )}
            <div className="employee-comment"><b>Comentario del empleado</b><p>{e.comentario ? `“${e.comentario}”` : "Sin comentario."}</p></div>
            {e.revision && (
              <div className="employee-comment"><b>Revisión · {e.revision.decision === "APROBADA" ? "Aprobada" : "Devuelta"} por {e.revision.revisor}</b><p>{e.revision.observaciones || "Sin observaciones."} · {fechaHora(e.revision.revisada_en)}</p></div>
            )}
          </section>
          <section className="space-y-4">
            <div className="admin-card">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div className="min-w-0"><Link to={`/tareas/${t.id}`} className="text-sm font-extrabold text-slate-800 hover:text-wine">{t.titulo}</Link><p className="mt-1 text-[10px] text-slate-400">{t.ubicacion || t.codigo}</p></div>
                <Badge tipo="tarea" estado={t.estado}>{t.estado_display}</Badge>
              </div>
              <div className="review-meta">
                <span><small>Empleado</small><b>{e.empleado.nombre}</b></span>
                <span><small>Servicio</small><b>{t.tipo_servicio}</b></span>
                <span><small>Prioridad</small><b>{t.prioridad_display}</b></span>
                <span><small>Fecha límite</small><b>{vence(t.fecha_limite, t.vencida)}</b></span>
              </div>
              {t.criterios_aceptacion && <><h3 className="detail-label">Criterios de aceptación</h3><div className="detail-copy">{criterios(t.criterios_aceptacion).map((c) => <p key={c}>{c}</p>)}</div></>}
              <h3 className="detail-label">Lista de verificación</h3>
              <div className="review-checks">
                {t.items.map((x) => <div key={x.id}><span className={x.completado ? "" : "!bg-slate-200"}>{x.completado && <Icon name="check" size={13} />}</span>{x.descripcion}</div>)}
                {!t.items.length && <p className="detail-copy">Sin lista de verificación.</p>}
              </div>
              {anteriores.map((v) => (
                <Link key={v.id} to={`/entregas/${v.id}`} className="version-link"><Icon name="history" size={16} />Ver versión {v.version} · {v.estado_display.toLowerCase()}<Icon name="chevron" size={15} /></Link>
              ))}
            </div>
            {errores.length > 0 && <ErrorBox mensajes={errores} />}
            {devolviendo && e.estado === "EN_REVISION" && (
              <div className="return-box">
                <label htmlFor="obs">Observaciones para el empleado *</label>
                <textarea id="obs" autoFocus value={observaciones} onChange={(ev) => setObservaciones(ev.target.value)} placeholder="Explica claramente qué debe corregir..." />
                <div>
                  <button onClick={() => setDevolviendo(false)}>Cancelar</button>
                  <button onClick={() => revisar("devolver")} disabled={ocupado || !observaciones.trim()}>Confirmar devolución</button>
                </div>
              </div>
            )}
            {e.estado === "EN_REVISION" && !aprobada && (
              <div className="review-actions">
                <button className="approve" onClick={() => revisar("aprobar")} disabled={ocupado}><Icon name="check" />Aprobar</button>
                <button className="return" onClick={() => setDevolviendo(true)} disabled={ocupado}><Icon name="alert" />Devolver</button>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
