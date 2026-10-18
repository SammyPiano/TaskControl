import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import Avatar from "@/components/Avatar";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import MenuFila from "@/components/MenuFila";
import Paginacion from "@/components/Paginacion";
import Prioridad from "@/components/Prioridad";
import { query, type Pagina } from "@/lib/api";
import { vence } from "@/lib/formato";
import type { Opcion, Persona, TareaResumen } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

type Opciones = { empleados: Persona[]; prioridades: Opcion[]; estados: Opcion[] };
const POR_PAGINA = 20;

export default function Tareas() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [texto, setTexto] = useState(params.get("q") ?? "");
  const filtro = (clave: string) => params.get(clave) ?? "";
  const pagina = Number(params.get("page") ?? 1);
  const { datos: opciones } = useApi<Opciones>("tareas/opciones/");
  const ruta = `tareas/${query({ q: filtro("q"), estado: filtro("estado"), prioridad: filtro("prioridad"), empleado: filtro("empleado"), desde: filtro("desde"), hasta: filtro("hasta"), page: pagina > 1 ? pagina : "" })}`;
  const { datos, errores, cargando } = useApi<Pagina<TareaResumen>>(ruta);

  useEffect(() => setTexto(params.get("q") ?? ""), [params]);
  useEffect(() => {
    const t = setTimeout(() => texto !== filtro("q") && cambiar("q", texto), 350);
    return () => clearTimeout(t);
  }, [texto]); // eslint-disable-line react-hooks/exhaustive-deps

  function cambiar(clave: string, valor: string) {
    const nuevos = new URLSearchParams(params);
    if (valor) nuevos.set(clave, valor);
    else nuevos.delete(clave);
    if (clave !== "page") nuevos.delete("page");
    setParams(nuevos, { replace: true });
  }

  return (
    <>
      <Heading title="Tareas" description="Consulta, asigna y da seguimiento a todos los servicios de campo.">
        <Link className="admin-primary" to="/tareas/nueva"><Icon name="plus" size={17} />Nueva tarea</Link>
      </Heading>
      <section className="admin-card !p-0">
        <div className="filters-row">
          <div className="filter-search"><Icon name="search" size={17} /><input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Buscar por tarea, código o ubicación..." aria-label="Buscar" /></div>
          <select value={filtro("estado")} onChange={(e) => cambiar("estado", e.target.value)} aria-label="Estado">
            <option value="">Todos los estados</option>
            {opciones?.estados.map((o) => <option key={o.valor} value={o.valor}>{o.etiqueta}</option>)}
            <option value="VENCIDA">Vencidas</option>
          </select>
          <select value={filtro("prioridad")} onChange={(e) => cambiar("prioridad", e.target.value)} aria-label="Prioridad">
            <option value="">Todas las prioridades</option>
            {opciones?.prioridades.map((o) => <option key={o.valor} value={o.valor}>{o.etiqueta}</option>)}
          </select>
          <select value={filtro("empleado")} onChange={(e) => cambiar("empleado", e.target.value)} aria-label="Empleado">
            <option value="">Todos los empleados</option>
            {opciones?.empleados.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
          </select>
          <input type="date" value={filtro("desde")} onChange={(e) => cambiar("desde", e.target.value)} aria-label="Fecha límite desde" title="Fecha límite desde" />
          <input type="date" value={filtro("hasta")} onChange={(e) => cambiar("hasta", e.target.value)} aria-label="Fecha límite hasta" title="Fecha límite hasta" />
        </div>
        <ErrorBox mensajes={errores} />
        {cargando && !datos && <div className="p-5"><Cargando filas={5} alto="h-12" /></div>}
        {datos && (
          <div className="table-scroll">
            <table className="tabla-tareas">
              <thead><tr><th>Tarea</th><th>Empleado</th><th>Servicio</th><th>Prioridad</th><th>Fecha límite</th><th>Estado</th><th>Avance</th><th>Acciones</th></tr></thead>
              <tbody>
                {datos.results.map((t) => (
                  <tr key={t.id} className="clicable" onClick={() => navigate(`/tareas/${t.id}`)}>
                    <td><Link to={`/tareas/${t.id}`} className="enlace-fila" title={t.titulo} onClick={(e) => e.stopPropagation()}><b className="block text-slate-800">{t.titulo}</b><small className="text-slate-400">{t.codigo}{t.ubicacion && ` · ${t.ubicacion}`}</small></Link></td>
                    <td><div className="flex items-center gap-2"><Avatar size="small">{t.asignado.iniciales}</Avatar>{t.asignado.nombre}</div></td>
                    <td className="servicio">{t.tipo_servicio}</td>
                    <td><Prioridad valor={t.prioridad}>{t.prioridad_display}</Prioridad></td>
                    <td className={t.vencida ? "!font-bold !text-red-600" : ""}>{vence(t.fecha_limite, t.vencida)}</td>
                    <td><Badge tipo="tarea" estado={t.estado}>{t.estado_display}</Badge></td>
                    <td><div className="progress-cell"><i><span style={{ width: `${t.progreso.porcentaje}%` }} /></i>{t.progreso.porcentaje}%</div></td>
                    <td>
                      <MenuFila etiqueta={`Acciones de ${t.codigo}`}>
                        <Link to={`/tareas/${t.id}`} role="menuitem"><Icon name="eye" size={17} />Ver detalle</Link>
                        {["PENDIENTE", "EN_PROCESO", "DEVUELTA"].includes(t.estado) && <Link to={`/tareas/${t.id}/editar`} role="menuitem"><Icon name="edit" size={17} />Editar</Link>}
                        <Link to={`/historial?entidad=tarea&entidad_id=${t.id}`} role="menuitem"><Icon name="history" size={17} />Ver historial</Link>
                      </MenuFila>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!datos.results.length && <div className="empty-state">No hay tareas con estos filtros.</div>}
          </div>
        )}
        {datos && <Paginacion pagina={pagina} total={datos.count} porPagina={POR_PAGINA} onCambiar={(p) => cambiar("page", String(p))} />}
      </section>
    </>
  );
}
