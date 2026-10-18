import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MenuFila from "@/components/MenuFila";
import MobileHeader from "@/components/MobileHeader";
import Prioridad from "@/components/Prioridad";
import { api, mensajesDe } from "@/lib/api";
import { vence } from "@/lib/formato";
import type { TareaDetalle as Tarea } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

/** Criterios como lista: una línea por criterio (o una oración por criterio si vienen en un párrafo). */
export function criterios(texto: string): string[] {
  const lineas = texto.split("\n").map((l) => l.trim()).filter(Boolean);
  return lineas.length > 1 ? lineas : texto.split(/(?<=\.)\s+/).map((l) => l.trim()).filter(Boolean);
}

export default function TareaDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { datos: tarea, setDatos, errores, setErrores } = useApi<Tarea>(`tareas/${id}/`);
  const [ocupado, setOcupado] = useState(false);

  const accion = async (fn: () => Promise<Tarea>) => {
    setOcupado(true);
    try {
      setDatos(await fn());
      setErrores([]);
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setOcupado(false);
    }
  };

  const iniciada = tarea && tarea.estado !== "PENDIENTE";
  const marcar = (itemId: number, completado: boolean) =>
    accion(() => api<Tarea>(`items/${itemId}/marcar/`, { method: "POST", body: { completado } }));
  const iniciar = () => accion(() => api<Tarea>(`tareas/${id}/iniciar/`, { method: "POST" }));
  const hechos = tarea?.items.filter((i) => i.completado).length ?? 0;

  const menu = (
    <MenuFila etiqueta="Más opciones">
      <Link to={`/tareas/${id}/entregas`} role="menuitem"><Icon name="history" size={18} />Historial de entregas</Link>
      {tarea?.abierta && <Link to={`/viaticos/solicitar?tarea=${id}`} role="menuitem"><Icon name="wallet" size={18} />Solicitar viático</Link>}
    </MenuFila>
  );

  return (
    <>
      <MobileHeader title="Detalle de la tarea" back={() => navigate("/")} action={menu} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <ErrorBox mensajes={errores} />
        {!tarea && !errores.length && <Cargando filas={4} alto="h-28" />}
        {tarea && (
          <>
            <div className="mb-3 mt-1 flex flex-wrap gap-2">
              <Badge tipo="tarea" estado={tarea.estado}>{tarea.estado_display}</Badge>
              <Prioridad valor={tarea.prioridad}>{tarea.prioridad_display}</Prioridad>
              {tarea.vencida && <span className="badge badge-red">Vencida</span>}
            </div>
            <h2 className="mb-2 text-xl font-extrabold leading-tight text-slate-900">{tarea.titulo}</h2>
            <p className="mb-5 text-sm text-slate-500">Tarea #{tarea.codigo} · {tarea.tipo_servicio} · {vence(tarea.fecha_limite, tarea.vencida)}</p>

            {tarea.descripcion && (
              <section className="content-card mb-3">
                <div className="section-title">Descripción</div>
                <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">{tarea.descripcion}</p>
              </section>
            )}
            {tarea.ubicacion && (
              <section className="content-card mb-3">
                <div className="mb-3 flex items-start gap-3">
                  <div className="round-icon"><Icon name="pin" size={18} /></div>
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-slate-800">Ubicación</div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">{tarea.ubicacion}</p>
                  </div>
                </div>
                <a className="secondary-button" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(tarea.ubicacion)}`} target="_blank" rel="noreferrer">
                  <Icon name="map" size={18} />Abrir en mapas
                </a>
              </section>
            )}
            {tarea.criterios_aceptacion && (
              <section className="content-card mb-3">
                <div className="section-title">Criterios de aceptación</div>
                <ul className="space-y-2 text-sm text-slate-600">
                  {criterios(tarea.criterios_aceptacion).map((c) => <li key={c} className="flex gap-2"><span className="mt-0.5 shrink-0 text-wine"><Icon name="check" size={17} /></span><span>{c}</span></li>)}
                </ul>
              </section>
            )}
            <section className="content-card">
              <div className="mb-4 flex items-center justify-between"><div className="section-title !mb-0">Lista de verificación</div><span className="text-xs font-bold text-wine">{hechos}/{tarea.items.length}</span></div>
              {!tarea.items.length && <p className="text-xs text-slate-400">Esta tarea no tiene lista de verificación.</p>}
              <div className="divide-y divide-slate-100">
                {tarea.items.map((item) => (
                  <button key={item.id} disabled={!iniciada || !tarea.abierta || ocupado} onClick={() => marcar(item.id, !item.completado)} className="flex min-h-12 w-full items-center gap-3 border-0 bg-transparent py-3 text-left text-sm text-slate-700 disabled:opacity-50" role="checkbox" aria-checked={item.completado}>
                    <span className={`checkbox ${item.completado ? "checked" : ""}`}>{item.completado && <Icon name="check" size={14} />}</span>
                    <span>{item.descripcion}{item.obligatorio && <b className="ml-1 text-wine" aria-label="obligatorio">*</b>}</span>
                  </button>
                ))}
              </div>
              {!iniciada && tarea.items.length > 0 && <p className="mt-2 text-xs text-slate-400">Inicia la tarea para marcar los ítems. <b className="text-wine">*</b> Obligatorio.</p>}
            </section>
          </>
        )}
      </div>
      {tarea && (
        <div className="mobile-sticky-action">
          {!iniciada ? (
            <button className="primary-button" onClick={iniciar} disabled={ocupado}>{ocupado ? "Iniciando…" : "Iniciar tarea"}</button>
          ) : tarea.abierta ? (
            <Link className="primary-button" to={`/tareas/${id}/evidencias`}>Continuar a evidencias</Link>
          ) : (
            <Link className="secondary-button" to={`/tareas/${id}/entregas`}><Icon name="history" size={18} />{tarea.estado === "EN_REVISION" ? "En revisión · ver entregas" : "Ver historial de entregas"}</Link>
          )}
        </div>
      )}
    </>
  );
}
