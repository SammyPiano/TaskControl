import { NavLink } from "react-router";
import { NAV_EMPLEADO } from "@/lib/navegacion";
import { useSesion } from "@/lib/sesion";
import Icon from "./Icon";

export default function BottomNav() {
  const { usuario } = useSesion();
  const sinLeer = usuario?.notificaciones_sin_leer ?? 0;
  return (
    <nav className="bottom-nav" aria-label="Menú principal">
      {NAV_EMPLEADO.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
          <div className="relative">
            <Icon name={item.icon} size={21} />
            {item.to === "/notificaciones" && sinLeer > 0 && <span className="notification-dot -right-0.5 -top-0.5" />}
          </div>
          <span>{item.etiqueta}</span>
        </NavLink>
      ))}
    </nav>
  );
}
