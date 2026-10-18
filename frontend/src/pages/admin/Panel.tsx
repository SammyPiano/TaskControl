import { useEffect, useState } from "react";
import { Link } from "react-router";
import Avatar from "@/components/Avatar";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import Stat from "@/components/Stat";
import { api, mensajesDe } from "@/lib/api";
import { plural, rd, relativo } from "@/lib/formato";
import { useSesion } from "@/lib/sesion";

type DatosPanel = {
  mes: string;
  kpis: {
    pendientes: number;
    creadas_hoy: number;
    en_revision: number;
    urgentes_en_revision: number;
    vencidas: number;
    cumplimiento: number | null;
    viaticos_por_liquidar: number;
    monto_por_liquidar: string;
    gasto_mes: string;
    gastos_mes: number;
  };
  cumplimiento_empleados: { empleado: string; porcentaje: number }[];
  revisiones: {
    id: number;
    titulo: string;
    ubicacion: string;
    empleado: string;
    iniciales: string;
    version: number;
    fotos: number;
    presentada_en: string;
    urgente: boolean;
  }[];
};

export default function Panel() {
  const { usuario } = useSesion();
  const [datos, setDatos] = useState<DatosPanel | null>(null);
  const [errores, setErrores] = useState<string[]>([]);

  useEffect(() => {
    api<DatosPanel>("panel/").then(setDatos).catch((e) => setErrores(mensajesDe(e, "No se pudo cargar el panel.")));
  }, []);

  const k = datos?.kpis;
  return (
    <>
      <Heading title="Panel de control" description={`Supervisa las operaciones de ${usuario?.empresa?.nombre ?? "tu empresa"} en tiempo real.`}>
        <Link className="admin-primary" to="/tareas/nueva"><Icon name="plus" size={17} />Nueva tarea</Link>
      </Heading>
      <ErrorBox mensajes={errores} />
      {!datos && !errores.length && <Cargando filas={4} />}

      {k && datos && (
        <>
          <div className="kpi-grid">
            <Stat icon="tasks" label="Tareas pendientes" value={String(k.pendientes)} detail={`+${k.creadas_hoy} hoy`} tone="wine" />
            <Stat icon="review" label="En revisión" value={String(k.en_revision)} detail={plural(k.urgentes_en_revision, "urgente", "urgentes")} tone="amber" />
            <Stat icon="alert" label="Vencidas" value={String(k.vencidas)} detail="Fecha límite superada" tone="red" />
            <Stat icon="chart" label="Cumplimiento" value={k.cumplimiento === null ? "—" : `${k.cumplimiento}%`} detail={datos.mes} tone="blue" />
            <Stat icon="wallet" label="Viáticos por liquidar" value={String(k.viaticos_por_liquidar)} detail={rd(k.monto_por_liquidar)} tone="amber" />
            <Stat icon="wallet" label="Gasto del mes" value={rd(k.gasto_mes)} detail={plural(k.gastos_mes, "gasto aprobado", "gastos aprobados")} tone="blue" />
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.05fr_1fr]">
            <section className="admin-card">
              <div className="card-heading">
                <div>
                  <h2>Cumplimiento por empleado</h2>
                  <p>Tareas completadas sobre asignadas · {datos.mes}</p>
                </div>
                <Link to="/reportes">Ver reporte</Link>
              </div>
              {datos.cumplimiento_empleados.length ? (
                <div className="bar-chart" role="img" aria-label="Cumplimiento por empleado">
                  {datos.cumplimiento_empleados.slice(0, 6).map((f) => (
                    <div key={f.empleado} title={`${f.empleado}: ${f.porcentaje}%`}>
                      <b>{f.porcentaje}%</b>
                      <div className="bar-track"><span style={{ height: `${f.porcentaje}%` }} /></div>
                      <small>{f.empleado}</small>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">Aún no hay tareas asignadas este mes.</div>
              )}
              {datos.cumplimiento_empleados.length > 0 && <div className="mt-4 flex justify-center gap-2 text-[10px] text-slate-500"><i className="legend wine" /> Completadas sobre asignadas</div>}
            </section>

            <section className="admin-card !p-0">
              <div className="card-heading px-5 py-4">
                <div>
                  <h2>Entregas en revisión recientes</h2>
                  <p>{plural(k.en_revision, "entrega espera", "entregas esperan")} validación</p>
                </div>
                <Link to="/entregas">Ver todas</Link>
              </div>
              <div className="review-list">
                {datos.revisiones.map((r) => (
                  <Link key={r.id} to={`/entregas/${r.id}`}>
                    <Avatar>{r.iniciales}</Avatar>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <b className="truncate">{r.titulo}</b>
                        {r.urgente && <span className="priority priority-urgente">Urgente</span>}
                      </div>
                      <p>{r.empleado} · v{r.version} · {plural(r.fotos, "foto", "fotos")} · {relativo(r.presentada_en)}</p>
                      {r.ubicacion && <small className="truncate">{r.ubicacion}</small>}
                    </div>
                    <Icon name="chevron" size={17} />
                  </Link>
                ))}
                {!datos.revisiones.length && <div className="empty-state border-t border-slate-100">No hay entregas pendientes de revisión.</div>}
              </div>
            </section>
          </div>
        </>
      )}
    </>
  );
}
