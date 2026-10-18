import { Link, useParams } from "react-router";
import Avatar from "@/components/Avatar";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import Prioridad from "@/components/Prioridad";
import { fecha, fechaHora, plural, vence } from "@/lib/formato";
import type { TareaDetalle as Tarea } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";
import { criterios } from "@/pages/empleado/TareaDetalle";

export default function TareaDetalle() {
  const { id } = useParams();
  const { datos: t, errores } = useApi<Tarea>(`tareas/${id}/`);
  const enRevision = t?.entregas.find((e) => e.estado === "EN_REVISION");

  return (
    <>
      <Heading title={t ? `${t.titulo}` : "Tarea"} description={t ? `${t.codigo} · ${t.tipo_servicio} · creada por ${t.creado_por.nombre} el ${fecha(t.creada_en)}` : "Cargando…"}>
        <Link className="admin-secondary" to="/tareas"><Icon name="arrow" size={17} />Volver</Link>
        {t?.abierta && <Link className="admin-secondary" to={`/tareas/${id}/editar`}><Icon name="edit" size={17} />Editar</Link>}
        {enRevision && <Link className="admin-primary" to={`/entregas/${enRevision.id}`}><Icon name="review" size={17} />Revisar entrega</Link>}
      </Heading>
      <ErrorBox mensajes={errores} />
      {!t && !errores.length && <Cargando filas={4} />}
      {t && (
        <div className="review-layout">
          <section className="admin-card self-start">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div className="flex flex-wrap gap-2"><Badge tipo="tarea" estado={t.estado}>{t.estado_display}</Badge><Prioridad valor={t.prioridad}>{t.prioridad_display}</Prioridad>{t.vencida && <span className="badge badge-red">Vencida</span>}</div>
              <span className="text-xs font-bold text-wine">{t.progreso.porcentaje}% completado</span>
            </div>
            <div className="review-meta">
              <span><small>Empleado</small><b className="flex items-center gap-2"><Avatar size="small">{t.asignado.iniciales}</Avatar>{t.asignado.nombre}</b></span>
              <span><small>Servicio</small><b>{t.tipo_servicio}</b></span>
              <span><small>Fecha límite</small><b className={t.vencida ? "!text-red-600" : ""}>{vence(t.fecha_limite, t.vencida)}</b></span>
              <span><small>Ubicación</small><b>{t.ubicacion || "—"}</b></span>
            </div>
            {t.descripcion && <><h3 className="detail-label">Descripción</h3><p className="detail-copy whitespace-pre-line">{t.descripcion}</p></>}
            {t.criterios_aceptacion && <><h3 className="detail-label">Criterios de aceptación</h3><ul className="detail-copy list-disc pl-4">{criterios(t.criterios_aceptacion).map((c) => <li key={c}>{c}</li>)}</ul></>}
            <h3 className="detail-label">Lista de verificación · {t.progreso.hechos}/{t.progreso.total}</h3>
            <div className="review-checks">
              {t.items.map((x) => <div key={x.id}><span className={x.completado ? "" : "!bg-slate-200"}>{x.completado && <Icon name="check" size={13} />}</span>{x.descripcion}{x.obligatorio && <b className="text-wine">*</b>}</div>)}
              {!t.items.length && <p className="detail-copy">Sin lista de verificación.</p>}
            </div>
          </section>
          <section className="admin-card self-start">
            <div className="card-heading mb-4"><div><h2>Historial de entregas</h2><p>{plural(t.entregas.length, "versión presentada", "versiones presentadas")}</p></div><Link to={`/historial?entidad=tarea&entidad_id=${t.id}`}>Ver historial</Link></div>
            {!t.entregas.length && <div className="empty-state">El empleado aún no ha presentado entregas.</div>}
            {t.entregas.map((e) => (
              <Link key={e.id} to={`/entregas/${e.id}`} className="version-link">
                <Icon name="history" size={16} />
                <span className="min-w-0 flex-1 text-left"><b className="mr-2 text-slate-700">Versión {e.version}</b>{plural(e.fotos, "foto", "fotos")} · {fechaHora(e.presentada_en)}{e.revision?.observaciones && <span className="block text-orange-700">{e.revision.observaciones}</span>}</span>
                <Badge tipo="entrega" estado={e.estado}>{e.estado_display}</Badge>
                <Icon name="chevron" size={15} />
              </Link>
            ))}
            {t.completada_en && <div className="success-banner mt-4 !mb-0"><Icon name="check" /><div><b>Tarea completada</b><span>Aprobada el {fechaHora(t.completada_en)}.</span></div></div>}
          </section>
        </div>
      )}
    </>
  );
}
