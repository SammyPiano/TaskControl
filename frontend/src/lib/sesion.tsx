import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";

export type Usuario = {
  id: number;
  username: string;
  nombre: string;
  first_name: string;
  iniciales: string;
  email: string;
  rol: "EMPLEADO" | "ADMINISTRADOR";
  rol_display: string;
  cargo: string;
  telefono: string;
  zona: string;
  empresa: { id: number; nombre: string; rnc: string } | null;
  notificaciones_sin_leer: number;
  entregas_en_revision: number;
};

type Sesion = {
  usuario: Usuario | null;
  cargando: boolean;
  ingresar: (username: string, password: string) => Promise<Usuario>;
  salir: () => Promise<void>;
  refrescar: () => Promise<void>;
};

const SesionContext = createContext<Sesion | null>(null);

export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const refrescar = useCallback(async () => {
    const datos = await api<{ usuario: Usuario | null }>("sesion/");
    setUsuario(datos.usuario);
  }, []);

  useEffect(() => {
    refrescar().catch(() => setUsuario(null)).finally(() => setCargando(false));
  }, [refrescar]);

  const ingresar = useCallback(async (username: string, password: string) => {
    const datos = await api<{ usuario: Usuario }>("sesion/", { method: "POST", body: { username, password } });
    setUsuario(datos.usuario);
    return datos.usuario;
  }, []);

  const salir = useCallback(async () => {
    await api("sesion/", { method: "DELETE" });
    setUsuario(null);
    await refrescar(); // nueva cookie CSRF tras cerrar sesión
  }, [refrescar]);

  return <SesionContext.Provider value={{ usuario, cargando, ingresar, salir, refrescar }}>{children}</SesionContext.Provider>;
}

export function useSesion(): Sesion {
  const contexto = useContext(SesionContext);
  if (!contexto) throw new Error("useSesion fuera de SesionProvider");
  return contexto;
}

export const esAdministrador = (u: Usuario | null) => u?.rol === "ADMINISTRADOR";
