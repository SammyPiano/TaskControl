/** Cliente de la API de Django: sesión por cookie + CSRF, errores con mensajes en español. */

export class ApiError extends Error {
  status: number;
  mensajes: string[];

  constructor(status: number, mensajes: string[]) {
    super(mensajes.join(" "));
    this.status = status;
    this.mensajes = mensajes;
  }
}

function leerCookie(nombre: string): string {
  const par = document.cookie.split("; ").find((c) => c.startsWith(`${nombre}=`));
  return par ? decodeURIComponent(par.split("=")[1]) : "";
}

/** Aplana {"detail": [...]} o {"campo": [...]} de DRF en una lista de mensajes. */
function extraerMensajes(datos: unknown, status: number): string[] {
  if (!datos || typeof datos !== "object") {
    if (status === 403) return ["No tiene permiso para esta acción."];
    if (status === 404) return ["No se encontró el registro."];
    return ["Ocurrió un error. Intente de nuevo."];
  }
  return Object.values(datos as Record<string, unknown>).flatMap((v) => (Array.isArray(v) ? v.map(String) : [String(v)]));
}

type Opciones = { method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"; body?: unknown };

export async function api<T>(ruta: string, { method = "GET", body }: Opciones = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const esArchivo = body instanceof FormData;
  if (body !== undefined && !esArchivo) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = leerCookie("csrftoken");

  const respuesta = await fetch(`/api/${ruta}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : esArchivo ? body : JSON.stringify(body),
  });
  if (respuesta.status === 204) return undefined as T;
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw new ApiError(respuesta.status, extraerMensajes(datos, respuesta.status));
  return datos as T;
}

/** Mensajes para mostrar a partir de cualquier error. */
export function mensajesDe(error: unknown, defecto = "No se pudo completar la acción."): string[] {
  return error instanceof ApiError ? error.mensajes : [defecto];
}

/** ?clave=valor omitiendo vacíos. */
export function query(parametros: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(parametros)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

export type Pagina<T> = { count: number; next: string | null; previous: string | null; results: T[] };
