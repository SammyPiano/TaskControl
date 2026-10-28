import { useState } from "react";
import { useSearchParams } from "react-router";
import Avatar from "@/components/Avatar";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import { query } from "@/lib/api";
import { fecha, hoyIso, primeroDelMes, rd } from "@/lib/formato";
import { useApi } from "@/lib/useApi";

type Reporte = {
  tipo: string; titulo: string; descripcion: string; desde: string; hasta: string;
  columnas: { titulo: string; numero: boolean }[];
  filas: string[][];
  total: string[] | null;
  resumen: { cumplimiento: number | null; completadas: number; retrasadas: number; viaticos_liquidados: string };
  leyenda: [string, string];
  serie: { etiqueta: string; desde: string; hasta: string; a: number | string; b: number | string }[];
  pestanas: { tipo: string; nombre: string }[];
  empleados: { id: number; nombre: string }[];
};

const iniciales = (nombre: string) => nombre.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

export default function Reportes() {
  const [params] = useSearchParams();
  const [tipo, setTipo] = useState(params.get("tipo") ?? "cumplimiento");
  const [desde, setDesde] = useState(primeroDelMes());
  const [hasta, setHasta] = useState(hoyIso());
  const [empleado, setEmpleado] = useState("");
  const filtros = query({ desde, hasta, empleado });
  const { datos: r, errores, cargando } = useApi<Reporte>(`reportes/${tipo}/${filtros}`);
  const maximo = Math.max(1, ...(r?.serie.flatMap((s) => [Number(s.a), Number(s.b)]) ?? [1]));
  const valor = (v: number | string) => (tipo === "viaticos" ? rd(v) : String(v));
  const pestanas = r?.pestanas ?? [{ tipo: "cumplimiento", nombre: "Cumplimiento" }, { tipo: "pendientes", nombre: "Pendientes y retrasos" }, { tipo: "viaticos", nombre: "Viáticos" }];

  return (
    <>
      <Heading title="Reportes" description="Analiza productividad, retrasos y uso de viáticos.">
        <a className="admin-secondary" href={`/api/reportes/${tipo}/${filtros}${filtros ? "&" : "?"}formato=csv`} download><Icon name="download" size={17} />Exportar CSV</a>
      </Heading>
      <div className="report-toolbar">
        <div className="report-tabs" role="tablist">
          {pestanas.map((p) => <button key={p.tipo} role="tab" aria-selected={tipo === p.tipo} className={tipo === p.tipo ? "active" : ""} onClick={() => setTipo(p.tipo)}>{p.nombre}</button>)}
        </div>
        <input type="date" value={desde} max={hasta} onChange={(e) => setDesde(e.target.value)} aria-label="Desde" />
        <input type="date" value={hasta} min={desde} onChange={(e) => setHasta(e.target.value)} aria-label="Hasta" />
        <select value={empleado} onChange={(e) => setEmpleado(e.target.value)} aria-label="Empleado">
          <option value="">Todos los empleados</option>
          {r?.empleados.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
        </select>
      </div>
      <ErrorBox mensajes={errores} />
      {cargando && !r && <Cargando filas={3} alto="h-40" />}
      {r && (
        <>
          <div className="grid gap-5 lg:grid-cols-[1.4fr_.8fr]">
            <section className="admin-card">
              <div className="card-heading">
                <div><h2>{r.titulo} por semana</h2><p>{fecha(r.desde)} – {fecha(r.hasta)}</p></div>
                <div className="flex items-center gap-3 text-[10px] text-slate-500"><span className="flex items-center gap-1"><i className="legend wine" />{r.leyenda[0]}</span><span className="flex items-center gap-1"><i className="legend" style={{ background: "#75efff" }} />{r.leyenda[1]}</span></div>
              </div>
              <div className="report-chart" role="img" aria-label={`${r.titulo} por semana`}>
                {r.serie.map((s) => (
                  <div key={s.desde} title={`${s.etiqueta}: ${r.leyenda[0]} ${valor(s.a)} · ${r.leyenda[1]} ${valor(s.b)}`}>
                    <div><span style={{ height: `${(Number(s.a) / maximo) * 100}%` }} /><i style={{ height: `${(Number(s.b) / maximo) * 100}%` }} /></div>
                    <small>{s.etiqueta}</small>
                  </div>
                ))}
              </div>
            </section>
            <section className="admin-card">
              <div className="card-heading mb-5"><div><h2>Resumen</h2><p>Indicadores del período</p></div></div>
              <div className="report-summary">
                <div><span>{r.resumen.cumplimiento === null ? "—" : `${r.resumen.cumplimiento}%`}</span><small>Cumplimiento</small></div>
                <div><span>{r.resumen.completadas}</span><small>Tareas completadas</small></div>
                <div><span>{r.resumen.retrasadas}</span><small>Fuera de plazo o vencidas</small></div>
                <div><span>{rd(r.resumen.viaticos_liquidados)}</span><small>Viáticos liquidados</small></div>
              </div>
            </section>
          </div>
          <section className="admin-card mt-5 !p-0">
            <div className="card-heading px-5 py-4"><div><h2>Detalle {r.tipo === "pendientes" ? "de tareas sin completar" : "por empleado"}</h2><p>{r.descripcion}</p></div></div>
            <div className="table-scroll">
              <table>
                <thead><tr>{r.columnas.map((c) => <th key={c.titulo} className={c.numero ? "!text-right" : ""}>{c.titulo}</th>)}</tr></thead>
                <tbody>
                  {r.filas.map((f, i) => (
                    <tr key={i}>
                      {f.map((v, j) => (
                        <td key={j} className={r.columnas[j].numero ? "text-right" : ""}>
                          {j === 0 ? <div className="flex items-center gap-2"><Avatar size="small">{iniciales(v)}</Avatar><b>{v}</b></div> : v}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {r.total && <tr>{r.total.map((v, j) => <td key={j} className={`!font-bold ${r.columnas[j].numero ? "text-right" : ""}`}>{v}</td>)}</tr>}
                </tbody>
              </table>
              {!r.filas.length && <div className="empty-state">Sin datos en el período.</div>}
            </div>
          </section>
        </>
      )}
    </>
  );
}
