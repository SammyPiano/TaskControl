/** Formatos de pantalla: dd/mm/aaaa, hora de Santo Domingo y montos en RD$. */

const ZONA = "America/Santo_Domingo";
const fechaCorta = new Intl.DateTimeFormat("es-DO", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: ZONA });
const hora = new Intl.DateTimeFormat("es-DO", { hour: "numeric", minute: "2-digit", timeZone: ZONA });
const fechaLarga = new Intl.DateTimeFormat("es-DO", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: ZONA });
const diaMes = new Intl.DateTimeFormat("es-DO", { weekday: "long", day: "numeric", month: "long", timeZone: ZONA });
const iso = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: ZONA });
const numero = new Intl.NumberFormat("es-DO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const SOLO_FECHA = /^\d{4}-\d{2}-\d{2}$/;
const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** dd/mm/aaaa. Las fechas sin hora ("2025-06-12") no se convierten de zona. */
export function fecha(valor: string | Date): string {
  if (typeof valor === "string" && SOLO_FECHA.test(valor)) {
    const [a, m, d] = valor.split("-");
    return `${d}/${m}/${a}`;
  }
  return fechaCorta.format(new Date(valor));
}

export function fechaHora(valor: string | Date): string {
  const d = new Date(valor);
  return `${fechaCorta.format(d)} · ${hora.format(d)}`;
}

export function horaDe(valor: string | Date): string {
  return hora.format(new Date(valor));
}

/** Hoy en Santo Domingo como "aaaa-mm-dd". */
export function hoyIso(): string {
  return iso.format(new Date());
}

export function primeroDelMes(): string {
  return `${hoyIso().slice(0, 8)}01`;
}

export function hoyLargo(): string {
  return capital(fechaLarga.format(new Date()));
}

/** "Miércoles, 12 de junio" (saludo del empleado). */
export function hoyCorto(): string {
  return capital(diaMes.format(new Date()));
}

/** Texto de la fecha límite: "Hoy", "Mañana", "Venció 11/06/2025" o la fecha. */
export function vence(fechaLimite: string | null, vencida: boolean): string {
  if (!fechaLimite) return "Sin fecha límite";
  if (vencida) return `Venció ${fecha(fechaLimite)}`;
  const hoy = hoyIso();
  if (fechaLimite === hoy) return "Hoy";
  const manana = new Date(`${hoy}T12:00:00Z`);
  manana.setUTCDate(manana.getUTCDate() + 1);
  if (fechaLimite === manana.toISOString().slice(0, 10)) return "Mañana";
  return fecha(fechaLimite);
}

/** "Hace 12 min", "Hace 3 h", "Ayer, 3:42 p. m." o la fecha. */
export function relativo(valor: string): string {
  const d = new Date(valor);
  const minutos = Math.round((Date.now() - d.getTime()) / 60000);
  if (minutos < 1) return "Ahora";
  if (minutos < 60) return `Hace ${minutos} min`;
  if (minutos < 24 * 60) return `Hace ${Math.round(minutos / 60)} h`;
  if (minutos < 48 * 60) return `Ayer, ${hora.format(d)}`;
  return fechaCorta.format(d);
}

/** Los montos llegan como string decimal ("1234.50"); solo se formatean para mostrar. */
export function rd(monto: string | number | null | undefined): string {
  return `RD$ ${numero.format(Number(monto ?? 0))}`;
}

export function plural(n: number, uno: string, varios: string): string {
  return `${n} ${n === 1 ? uno : varios}`;
}

export function tamano(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
