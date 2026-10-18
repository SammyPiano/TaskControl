/** Formas de los datos que devuelve la API. Montos: string decimal; fechas: ISO. */

export type Persona = { id: number; nombre: string; iniciales: string };
export type Opcion = { valor: string; etiqueta: string };
export type Progreso = { hechos: number; total: number; porcentaje: number };

export type EstadoTarea = "PENDIENTE" | "EN_PROCESO" | "EN_REVISION" | "DEVUELTA" | "COMPLETADA" | "CANCELADA";
export type Prioridad = "BAJA" | "MEDIA" | "ALTA" | "URGENTE";

export type TareaResumen = {
  id: number;
  codigo: string;
  titulo: string;
  ubicacion: string;
  tipo_servicio: string;
  asignado: Persona;
  prioridad: Prioridad;
  prioridad_display: string;
  estado: EstadoTarea;
  estado_display: string;
  fecha_limite: string | null;
  vencida: boolean;
  progreso: Progreso;
};

export type ItemTarea = { id: number; descripcion: string; obligatorio: boolean; completado: boolean };

export type Revision = { decision: "APROBADA" | "DEVUELTA"; observaciones: string; revisor: string; revisada_en: string };

export type EntregaVersion = {
  id: number;
  version: number;
  estado: "EN_REVISION" | "APROBADA" | "DEVUELTA";
  estado_display: string;
  comentario: string;
  presentada_en: string;
  fotos: number;
  revision: Revision | null;
};

export type TareaDetalle = TareaResumen & {
  tipo_servicio_id: number;
  descripcion: string;
  criterios_aceptacion: string;
  creado_por: Persona;
  creada_en: string;
  completada_en: string | null;
  abierta: boolean;
  items: ItemTarea[];
  entregas: EntregaVersion[];
};

export type ItemPlantilla = { id?: number; descripcion: string; obligatorio: boolean };
export type TipoServicio = {
  id: number;
  nombre: string;
  usos: number;
  plantilla: { id: number; nombre: string; items: ItemPlantilla[] } | null;
};

export type EntregaPendiente = {
  id: number;
  version: number;
  presentada_en: string;
  fotos: number;
  empleado: Persona;
  tarea: { id: number; codigo: string; titulo: string; ubicacion: string; prioridad: Prioridad; prioridad_display: string };
};

export type EntregaDetalle = EntregaVersion & {
  empleado: Persona;
  evidencias: { id: number; descripcion: string; url: string }[];
  tarea: TareaDetalle;
};

export type EstadoViatico = "SOLICITADO" | "AUTORIZADO" | "RECHAZADO" | "ANTICIPO_ENTREGADO" | "EN_COMPROBACION" | "LIQUIDADO";

export type ViaticoResumen = {
  id: number;
  codigo: string;
  concepto: string;
  estado: EstadoViatico;
  estado_display: string;
  tarea: { id: number; codigo: string; titulo: string; ubicacion: string };
  empleado: Persona;
  monto_solicitado: string;
  monto_aprobado: string | null;
  anticipo_entregado: string;
  solicitado_en: string;
};

export type Gasto = {
  id: number;
  categoria: string;
  categoria_display: string;
  fecha: string;
  monto: string;
  descripcion: string;
  estado: "PENDIENTE" | "APROBADO" | "RECHAZADO";
  estado_display: string;
  observacion: string;
  comprobante: string;
};

export type ViaticoDetalle = ViaticoResumen & {
  observacion: string;
  autorizado_por: Persona | null;
  autorizado_en: string | null;
  admite_gastos: boolean;
  totales: { pendiente: string; aprobado: string; rechazado: string };
  saldo: string;
  resultado_previsto: string;
  gastos: Gasto[];
  liquidacion: {
    total_gastos: string;
    total_anticipo: string;
    saldo: string;
    resultado: "REEMBOLSO" | "DEVOLUCION" | "SALDADO";
    resultado_display: string;
    liquidado_por: string;
    liquidada_en: string;
  } | null;
};
