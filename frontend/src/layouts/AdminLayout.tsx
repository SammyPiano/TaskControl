import { useEffect, useState, type FormEvent } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import Avatar from "@/components/Avatar";
import Icon from "@/components/Icon";
import Logo from "@/components/Logo";
import { NAV_ADMIN } from "@/lib/navegacion";
import { useSesion } from "@/lib/sesion";

function Sidebar({ onSalir }: { onSalir: () => void }) {
  const { usuario } = useSesion();
  const enRevision = usuario?.entregas_en_revision ?? 0;
  return (
    <aside className="sidebar">
      <div className="px-6 py-7"><Logo /></div>
      <nav className="sidebar-nav px-3" aria-label="Menú principal">
        {NAV_ADMIN.map((grupo, i) => (
          <div key={grupo.titulo} className={i ? "mt-7" : ""}>
            <div className="sidebar-label">{grupo.titulo}</div>
            {grupo.items.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
                <Icon name={item.icon} size={19} />
                <span className={item.to === "/entregas" ? "bg-gradient-to-r from-cyan-700 to-lime-400 bg-clip-text font-bold text-transparent" : ""}>{item.etiqueta}</span>
                {item.to === "/entregas" && enRevision > 0 && <i>{enRevision}</i>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="admin-profile">
        <Avatar>{usuario?.iniciales}</Avatar>
        <div>
          <b className="truncate">{usuario?.nombre}</b>
          <span className="truncate">{usuario?.cargo || usuario?.rol_display}</span>
        </div>
        <button className="icon-button" onClick={onSalir} aria-label="Cerrar sesión" title="Cerrar sesión"><Icon name="logout" size={17} /></button>
      </div>
    </aside>
  );
}

export default function AdminLayout() {
  const { usuario, salir, refrescar } = useSesion();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [cajon, setCajon] = useState(false);
  const [menuUsuario, setMenuUsuario] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => {
    setCajon(false);
    setMenuUsuario(false);
    refrescar().catch(() => null); // contadores del menú y de notificaciones
  }, [pathname, refrescar]);

  const cerrarSesion = async () => {
    await salir();
    navigate("/ingresar", { replace: true });
  };
  const buscar = (e: FormEvent) => {
    e.preventDefault();
    const q = busqueda.trim();
    navigate(q ? `/tareas?q=${encodeURIComponent(q)}` : "/tareas");
  };
  const sinLeer = usuario?.notificaciones_sin_leer ?? 0;

  return (
    <div className="flex min-h-screen bg-surface">
      <div className="hidden lg:block"><Sidebar onSalir={cerrarSesion} /></div>
      {cajon && (
        <div className="lg:hidden">
          <div className="sidebar-drawer">
            <Sidebar onSalir={cerrarSesion} />
            <button onClick={() => setCajon(false)} aria-label="Cerrar menú" />
          </div>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <header className="admin-topbar">
          {/* Envoltorios: las utilidades de Tailwind no ganan al CSS de .icon-button */}
          <div className="mr-3 flex items-center gap-1 lg:hidden">
            <button className="icon-button" onClick={() => setCajon(true)} aria-label="Abrir menú"><Icon name="menu" /></button>
            <Logo compact />
          </div>
          <form className="admin-search" role="search" onSubmit={buscar}>
            <Icon name="search" size={19} />
            <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar tareas, ubicaciones o códigos..." aria-label="Buscar tareas" />
            <kbd>Enter</kbd>
          </form>
          <div className="ml-auto flex items-center gap-3">
            <Link to="/notificaciones" className="icon-button relative border border-slate-200 bg-white" aria-label={sinLeer ? `Notificaciones (${sinLeer} sin leer)` : "Notificaciones"}>
              <Icon name="bell" size={19} />
              {sinLeer > 0 && <span className="notification-dot right-1 top-1" />}
            </Link>
            <div className="h-7 w-px bg-slate-200" />
            <div className="relative">
              <button className="flex min-h-11 items-center gap-2 border-0 bg-transparent" onClick={() => setMenuUsuario(!menuUsuario)} aria-expanded={menuUsuario} aria-haspopup="menu" aria-label="Menú de usuario">
                <Avatar>{usuario?.iniciales}</Avatar>
                <span className="rotate-90 text-slate-500"><Icon name="chevron" size={15} /></span>
              </button>
              {menuUsuario && (
                <div className="user-menu" role="menu">
                  <div className="px-3 py-2 text-xs text-slate-500"><b className="block text-sm text-slate-800">{usuario?.nombre}</b>{usuario?.empresa?.nombre}</div>
                  <Link to="/perfil" role="menuitem"><Icon name="user" size={18} />Mi perfil</Link>
                  <button onClick={cerrarSesion} role="menuitem" className="!text-red-600"><Icon name="logout" size={18} />Cerrar sesión</button>
                </div>
              )}
            </div>
          </div>
        </header>
        <main className="admin-main"><Outlet /></main>
      </div>
    </div>
  );
}
