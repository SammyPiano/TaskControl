import { NavLink } from "react-router";
import { NAV_EMPLEADO } from "@/lib/navegacion";
import { useSesion } from "@/lib/sesion";
import Avatar from "./Avatar";
import Icon from "./Icon";
import Logo from "./Logo";

/** Menú del empleado: barra inferior en teléfono y tableta, barra lateral en escritorio. */
export default function BottomNav() {
  const { usuario } = useSesion();
  const sinLeer = usuario?.notificaciones_sin_leer ?? 0;
  return (
    <nav className="bottom-nav" aria-label="Menú principal">
      <div className="rail-logo"><Logo /></div>
      {NAV_EMPLEADO.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
          <div className="relative">
            <Icon name={item.icon} size={21} />
            {item.to === "/notificaciones" && sinLeer > 0 && <span className="notification-dot -right-0.5 -top-0.5" />}
          </div>
          <span>{item.etiqueta}</span>
        </NavLink>
      ))}
      {usuario && (
        <div className="rail-usuario">
          <Avatar>{usuario.iniciales}</Avatar>
          <div className="min-w-0"><b>{usuario.nombre}</b><small>{usuario.cargo || usuario.rol_display}</small></div>
        </div>
      )}
    </nav>
  );
}
