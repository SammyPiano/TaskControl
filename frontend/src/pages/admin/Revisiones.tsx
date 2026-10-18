import { Link } from "react-router";
import Avatar from "@/components/Avatar";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import { plural, relativo } from "@/lib/formato";
import type { EntregaPendiente } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

export default function Revisiones() {
  const { datos, errores } = useApi<EntregaPendiente[]>("entregas/");
  return (
    <>
      <Heading title="Entregas en revisión" description="Valida evidencias, listas y criterios de aceptación." />
      <ErrorBox mensajes={errores} />
      {!datos && !errores.length && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><Cargando filas={3} alto="h-48" /></div>}
      {datos && !datos.length && <section className="admin-card"><div className="empty-state">No hay entregas pendientes de revisión.</div></section>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {datos?.map((e) => (
          <Link className="review-card" key={e.id} to={`/entregas/${e.id}`}>
            <div className="flex justify-between gap-2">
              <Badge tipo="entrega" estado="EN_REVISION">{`En revisión · v${e.version}`}</Badge>
              {e.tarea.prioridad === "URGENTE" && <span className="priority priority-urgente">Urgente</span>}
            </div>
            <h3>{e.tarea.titulo}</h3>
            <p>{e.tarea.codigo}{e.tarea.ubicacion && ` · ${e.tarea.ubicacion}`}</p>
            <div className="review-card-footer">
              <Avatar size="small">{e.empleado.iniciales}</Avatar>
              <span>{e.empleado.nombre}<small>{plural(e.fotos, "foto", "fotos")} · {relativo(e.presentada_en)}</small></span>
              <Icon name="chevron" size={17} />
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
