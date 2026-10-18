import { useState } from "react";
import { Link } from "react-router";
import Badge from "@/components/Badge";
import BottomNav from "@/components/BottomNav";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import Logo from "@/components/Logo";
import Prioridad from "@/components/Prioridad";
import Progress from "@/components/Progress";
import { hoyCorto, hoyIso, plural, vence } from "@/lib/formato";
import { useSesion } from "@/lib/sesion";
import type { TareaResumen } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

const FILTROS = [
  { etiqueta: "Todas", aplica: () => true },
  { etiqueta: "Pendientes", aplica: (t: TareaResumen) => t.estado === "PENDIENTE" },
  { etiqueta: "En proceso", aplica: (t: TareaResumen) => t.estado === "EN_PROCESO" },
  { etiqueta: "Devueltas", aplica: (t: TareaResumen) => t.estado === "DEVUELTA" },
  { etiqueta: "En revisión", aplica: (t: TareaResumen) => t.estado === "EN_REVISION" },
  { etiqueta: "Vencidas", aplica: (t: TareaResumen) => t.vencida },
];

function TaskCard({ tarea }: { tarea: TareaResumen }) {
  const destino = tarea.estado === "DEVUELTA" ? `/tareas/${tarea.id}/entregas` : `/tareas/${tarea.id}`;
  const p = tarea.progreso;
  return (
    <Link to={destino} className="task-card block text-left">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap gap-1.5">
            <Badge tipo="tarea" estado={tarea.estado}>{tarea.estado_display}</Badge>
            <Prioridad valor={tarea.prioridad}>{tarea.prioridad_display}</Prioridad>
            {tarea.vencida && <span className="badge badge-red">Vencida</span>}
          </div>
          <div className="text-[15px] font-bold leading-snug text-slate-900">{tarea.titulo}</div>
        </div>
        <Icon name="chevron" size={18} />
      </div>
      {tarea.ubicacion && <div className="mb-1.5 flex items-center gap-2 text-xs text-slate-500"><Icon name="pin" size={15} /><span className="truncate">{tarea.ubicacion}</span></div>}
      <div className="mb-4 flex items-center gap-2 text-xs text-slate-500">
        <Icon name="calendar" size={15} />
        <span className={tarea.vencida ? "font-semibold text-red-600" : ""}>{vence(tarea.fecha_limite, tarea.vencida)}</span>
        <span className="ml-auto rounded-md bg-slate-50 px-2 py-1">{tarea.tipo_servicio}</span>
      </div>
      {p.total > 0 ? <Progress value={p.porcentaje} label={`${p.hechos}/${p.total}`} /> : <div className="text-xs text-slate-400">Sin lista de verificación</div>}
    </Link>
  );
}

export default function MisTareas() {
  const { usuario } = useSesion();
  const { datos: tareas, errores, cargando } = useApi<TareaResumen[]>("mis-tareas/");
  const [filtro, setFiltro] = useState("Todas");
  const sinLeer = usuario?.notificaciones_sin_leer ?? 0;
  const hoy = hoyIso();
  const deHoy = tareas?.filter((t) => t.fecha_limite === hoy || t.vencida).length ?? 0;
  const vencidas = tareas?.filter((t) => t.vencida).length ?? 0;
  const aplica = FILTROS.find((f) => f.etiqueta === filtro)!.aplica;
  const visibles = tareas?.filter(aplica) ?? [];

  return (
    <>
      <div className="mobile-scroll pb-28">
        <div className="px-5 pb-4 pt-7">
          <div className="mb-6 flex items-center justify-between">
            <Logo compact />
            <Link to="/notificaciones" className="icon-button relative bg-white shadow-sm" aria-label="Notificaciones">
              <Icon name="bell" />
              {sinLeer > 0 && <span className="notification-dot right-1 top-1" />}
            </Link>
          </div>
          <p className="mb-1 text-sm text-slate-500">{hoyCorto()}</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Hola, {usuario?.first_name || usuario?.nombre}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {tareas ? <>Tienes <b className="text-slate-700">{plural(deHoy, "tarea", "tareas")}</b> para hoy · {plural(tareas.length, "activa", "activas")}.</> : "Cargando tus tareas…"}
          </p>
        </div>
        <div className="chips no-scrollbar px-5 pb-4">
          {FILTROS.map((f) => (
            <button key={f.etiqueta} onClick={() => setFiltro(f.etiqueta)} className={filtro === f.etiqueta ? "active" : ""} aria-pressed={filtro === f.etiqueta}>
              {f.etiqueta}
              {f.etiqueta === "Vencidas" && vencidas > 0 && <span className="ml-1.5 rounded-full bg-red-100 px-1.5 text-[10px] text-red-700">{vencidas}</span>}
            </button>
          ))}
        </div>
        <div className="space-y-3 px-5">
          <ErrorBox mensajes={errores} />
          {cargando && !tareas && <Cargando filas={3} alto="h-40" />}
          {visibles.map((t) => <TaskCard key={t.id} tarea={t} />)}
          {tareas && !visibles.length && <div className="rounded-xl border border-dashed border-slate-300 p-7 text-center text-xs text-slate-400">No hay tareas en este filtro.</div>}
        </div>
      </div>
      <BottomNav />
    </>
  );
}
