import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import Avatar from "@/components/Avatar";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import Stat from "@/components/Stat";
import { query } from "@/lib/api";
import { fecha, rd } from "@/lib/formato";
import type { Persona, ViaticoResumen } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

const ESTADOS = [
  ["SOLICITADO", "Solicitado"], ["AUTORIZADO", "Autorizado"], ["ANTICIPO_ENTREGADO", "Anticipo entregado"],
  ["EN_COMPROBACION", "En comprobación"], ["LIQUIDADO", "Liquidado"], ["RECHAZADO", "Rechazado"],
];

export default function Viaticos() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const estado = params.get("estado") ?? "";
  const empleado = params.get("empleado") ?? "";
  const { datos, errores, cargando } = useApi<{ resultados: ViaticoResumen[] }>(`viaticos/${query({ estado, empleado })}`);
  const { datos: opciones } = useApi<{ empleados: Persona[] }>("tareas/opciones/");
  const cambiar = (clave: string, valor: string) => {
    const nuevos = new URLSearchParams(params);
    if (valor) nuevos.set(clave, valor); else nuevos.delete(clave);
    setParams(nuevos, { replace: true });
  };
  const texto = q.trim().toLowerCase();
  const lista = datos?.resultados.filter((v) => !texto || `${v.codigo} ${v.concepto} ${v.empleado.nombre} ${v.tarea.titulo} ${v.tarea.codigo}`.toLowerCase().includes(texto));
  const todos = datos?.resultados ?? [];
  const contar = (...e: string[]) => todos.filter((v) => e.includes(v.estado)).length;

  return (
    <>
      <Heading title="Viáticos" description="Autoriza solicitudes, entrega anticipos, revisa comprobantes y liquida." />
      {!estado && datos && (
        <div className="mb-5 grid gap-4 sm:grid-cols-3">
          <Stat icon="clock" label="Por autorizar" value={String(contar("SOLICITADO"))} detail="Solicitudes nuevas" tone="amber" />
          <Stat icon="file" label="En comprobación" value={String(contar("AUTORIZADO", "ANTICIPO_ENTREGADO", "EN_COMPROBACION"))} detail="Pendientes de liquidar" tone="blue" />
          <Stat icon="check" label="Liquidados" value={String(contar("LIQUIDADO"))} detail="Cerrados" tone="wine" />
        </div>
      )}
      <section className="admin-card !p-0">
        <div className="filters-row">
          <div className="filter-search"><Icon name="search" size={17} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar concepto, empleado o tarea..." aria-label="Buscar" /></div>
          <select value={estado} onChange={(e) => cambiar("estado", e.target.value)} aria-label="Estado">
            <option value="">Todos los estados</option>
            {ESTADOS.map(([v, e]) => <option key={v} value={v}>{e}</option>)}
          </select>
          <select value={empleado} onChange={(e) => cambiar("empleado", e.target.value)} aria-label="Empleado">
            <option value="">Todos los empleados</option>
            {opciones?.empleados.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
          </select>
        </div>
        <ErrorBox mensajes={errores} />
        {cargando && !datos && <div className="p-5"><Cargando filas={4} alto="h-12" /></div>}
        {lista && (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Solicitud</th><th>Empleado</th><th>Tarea</th><th>Solicitado</th><th>Aprobado</th><th>Anticipo</th><th>Fecha</th><th>Estado</th></tr></thead>
              <tbody>
                {lista.map((v) => (
                  <tr key={v.id} className="clicable" onClick={() => navigate(`/viaticos/${v.id}`)}>
                    <td><Link to={`/viaticos/${v.id}`} className="enlace-fila" onClick={(e) => e.stopPropagation()}><b className="block text-slate-800">{v.concepto}</b><small className="text-slate-400">{v.codigo}</small></Link></td>
                    <td><div className="flex items-center gap-2"><Avatar size="small">{v.empleado.iniciales}</Avatar>{v.empleado.nombre}</div></td>
                    <td>{v.tarea.codigo}</td>
                    <td><b>{rd(v.monto_solicitado)}</b></td>
                    <td>{v.monto_aprobado ? rd(v.monto_aprobado) : "—"}</td>
                    <td>{rd(v.anticipo_entregado)}</td>
                    <td>{fecha(v.solicitado_en)}</td>
                    <td><Badge tipo="viatico" estado={v.estado}>{v.estado_display}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!lista.length && <div className="empty-state">No hay viáticos con estos filtros.</div>}
          </div>
        )}
      </section>
    </>
  );
}
