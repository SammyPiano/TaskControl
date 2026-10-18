import { useEffect } from "react";
import { Outlet, useLocation } from "react-router";
import { useSesion } from "@/lib/sesion";

/** Armazón de teléfono del empleado; cada pantalla decide si muestra la barra inferior o una acción fija. */
export default function MobileLayout() {
  const { refrescar } = useSesion();
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
    refrescar().catch(() => null); // punto de notificaciones sin leer
  }, [pathname, refrescar]);
  return <main className="mobile-app"><Outlet /></main>;
}
