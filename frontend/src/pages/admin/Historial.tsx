import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import Avatar from "@/components/Avatar";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon, { type IconName } from "@/components/Icon";
import Paginacion from "@/components/Paginacion";
import { query, type Pagina } from "@/lib/api";
import { fechaHora } from "@/lib/formato";
import { rutaSpa } from "@/lib/navegacion";
import type { Persona } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

type Evento = { id: number; usuario: Persona; entidad: string; entidad_display: string; entidad_id: number; accion: string; detalle: string; fecha: string; enlace: string };

/** Color e ícono del punto según la acción. */
function tono(accion: string): [string, IconName] {
  const a = accion.toLowerCase();
  if (a.includes("aprobad") || a.includes("liquidado") || a.includes("autorizado")) return ["green", "check"];
  if (a.includes("devuelta") || a.includes("rechazad")) return ["amber", "alert"];
  if (a.includes("gasto") || a.includes("anticipo") || a.includes("solicitado")) return ["wine", "wallet"];
  return ["blue", "tasks"];
}
const codigo = (e: Evento) => `${e.entidad === "tarea" ? "TC" : "VIA"}-${String(e.entidad_id).padStart(4, "0")}`;

export default function Historial() {
  const [params, setParams] = useSearchParams();
  const [texto, setTexto] = useState(params.get("q") ?? "");
  const f = (clave: string) => params.get(clave) ?? "";
  const pagina = Number(f("page") || 1);
  const filtros = { q: f("q"), accion: f("accion"), entidad: f("entidad"), entidad_id: f("entidad_id"), desde: f("desde"), hasta: f("hasta") };
  const { datos, errores, cargando } = useApi<Pagina<Evento> & { acciones: string[] }>(`historial/${query({ ...filtros, page: pagina > 1 ? pagina : "" })}`);

  function cambiar(clave: string, valor: string) {
    const nuevos = new URLSearchParams(params);
    if (valor) nuevos.set(clave, valor); else nuevos.delete(clave);
    if (clave !== "page") nuevos.delete("page");
    setParams(nuevos, { replace: true });
  }
  useEffect(() => {
    const t = setTimeout(() => texto !== f("q") && cambiar("q", texto), 350);
    return () => clearTimeout(t);
  }, [texto]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <Heading title="Historial" description="Registro cronológico de acciones y cambios de estado.">
        <a className="admin-secondary" href={`/api/historial/${query({ ...filtros, formato: "csv" })}`} download><Icon name="download" size={17} />Exportar CSV</a>
      </Heading>
      <section className="admin-card">
        <div className="filters-row !border-0 !p-0 pb-5">
          <div className="filter-search"><Icon name="search" size={17} /><input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Buscar usuario, tarea o acción..." aria-label="Buscar" /></div>
          <select value={f("accion")} onChange={(e) => cambiar("accion", e.target.value)} aria-label="Acción">
            <option value="">Todas las acciones</option>
            {datos?.acciones.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={f("entidad")} onChange={(e) => { cambiar("entidad", e.target.value); }} aria-label="Tipo de registro">
            <option value="">Tareas y viáticos</option><option value="tarea">Tareas</option><option value="viatico">Viáticos</option>
          </select>
          <input type="date" value={f("desde")} onChange={(e) => cambiar("desde", e.target.value)} aria-label="Desde" />
          <input type="date" value={f("hasta")} onChange={(e) => cambiar("hasta", e.target.value)} aria-label="Hasta" />
          {f("entidad_id") && <button onClick={() => { const n = new URLSearchParams(params); n.delete("entidad_id"); n.delete("entidad"); setParams(n); }}><Icon name="x" size={16} />Solo {f("entidad") === "tarea" ? "TC" : "VIA"}-{f("entidad_id").padStart(4, "0")}</button>}
        </div>
        <ErrorBox mensajes={errores} />
        {cargando && !datos && <Cargando filas={4} />}
        {datos && (
          <div className="history-timeline">
            {datos.results.map((e) => {
              const [color, icono] = tono(e.accion);
              return (
                <Link key={e.id} to={rutaSpa(e.enlace) ?? "/historial"}>
                  <div className={`history-dot ${color}`}><Icon name={icono} size={16} /></div>
                  <Avatar size="small">{e.usuario.iniciales}</Avatar>
                  <div className="flex-1"><p><b>{e.usuario.nombre}</b> · {e.accion.toLowerCase()} · {e.entidad_display} #{codigo(e)}</p><span className="truncate">{e.detalle}</span></div>
                  <time dateTime={e.fecha}>{fechaHora(e.fecha)}</time>
                </Link>
              );
            })}
            {!datos.results.length && <div className="empty-state">No hay registros con estos filtros.</div>}
          </div>
        )}
      </section>
      {datos && datos.count > 30 && <div className="admin-card mt-4 !p-0"><Paginacion pagina={pagina} total={datos.count} porPagina={30} onCambiar={(p) => cambiar("page", String(p))} /></div>}
    </>
  );
}
