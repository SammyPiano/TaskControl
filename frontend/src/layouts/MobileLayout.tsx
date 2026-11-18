import { useEffect } from "react";
import { Outlet, useLocation } from "react-router";
import BottomNav from "@/components/BottomNav";
import { NAV_EMPLEADO } from "@/lib/navegacion";
import { useSesion } from "@/lib/sesion";

/**
 * Armazón del empleado a pantalla completa. El menú va abajo en teléfono y tableta (solo en las pantallas
 * principales; las demás muestran su acción fija) y a la izquierda en escritorio (siempre visible).
 */
export default function MobileLayout() {
  const { refrescar } = useSesion();
  const { pathname } = useLocation();
  const principal = NAV_EMPLEADO.some((item) => item.to === pathname);
  useEffect(() => {
    window.scrollTo(0, 0);
    refrescar().catch(() => null); // punto de notificaciones sin leer
  }, [pathname, refrescar]);
  return (
    <div className={`mobile-app ${principal ? "con-menu" : ""}`}>
      <BottomNav />
      <main className="mobile-main"><Outlet /></main>
    </div>
  );
}
