import { useCallback, useEffect, useState } from "react";
import { api, mensajesDe } from "./api";

/** Carga `ruta` de la API (y la vuelve a cargar cuando cambia). `ruta` null = no cargar. */
export function useApi<T>(ruta: string | null) {
  const [datos, setDatos] = useState<T | null>(null);
  const [errores, setErrores] = useState<string[]>([]);
  const [cargando, setCargando] = useState(ruta !== null);

  const recargar = useCallback(async () => {
    if (ruta === null) return;
    setCargando(true);
    try {
      setDatos(await api<T>(ruta));
      setErrores([]);
    } catch (e) {
      setErrores(mensajesDe(e, "No se pudo cargar la información."));
    } finally {
      setCargando(false);
    }
  }, [ruta]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  return { datos, setDatos, errores, setErrores, cargando, recargar };
}
