/** Colores de estado y prioridad del diseño (clases badge-* / priority-* de index.css). */

const TAREA: Record<string, string> = {
  PENDIENTE: "badge-neutral",
  EN_PROCESO: "badge-blue",
  EN_REVISION: "badge-amber",
  DEVUELTA: "badge-orange",
  COMPLETADA: "badge-green",
  CANCELADA: "badge-cancel",
};
const ENTREGA: Record<string, string> = { EN_REVISION: "badge-amber", APROBADA: "badge-green", DEVUELTA: "badge-orange" };
const VIATICO: Record<string, string> = {
  SOLICITADO: "badge-neutral",
  AUTORIZADO: "badge-blue",
  RECHAZADO: "badge-red",
  ANTICIPO_ENTREGADO: "badge-blue",
  EN_COMPROBACION: "badge-amber",
  LIQUIDADO: "badge-green",
};
const GASTO: Record<string, string> = { PENDIENTE: "badge-amber", APROBADO: "badge-green", RECHAZADO: "badge-red" };

const CLASES = { tarea: TAREA, entrega: ENTREGA, viatico: VIATICO, gasto: GASTO };
export type TipoEstado = keyof typeof CLASES;

export function claseEstado(tipo: TipoEstado, estado: string): string {
  return CLASES[tipo][estado] ?? "badge-neutral";
}

export function clasePrioridad(prioridad: string): string {
  return `priority priority-${prioridad.toLowerCase()}`;
}
