import { Link, useNavigate } from "react-router";
import Avatar from "@/components/Avatar";
import BottomNav from "@/components/BottomNav";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { esAdministrador, useSesion } from "@/lib/sesion";
import type { TareaResumen } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

export default function Perfil() {
  const { usuario, salir } = useSesion();
  const navigate = useNavigate();
  const admin = esAdministrador(usuario);
  const { datos: tareas } = useApi<TareaResumen[]>(admin ? null : "mis-tareas/");
  if (!usuario) return null;
  const devuelta = tareas?.find((t) => t.estado === "DEVUELTA");

  const cerrarSesion = async () => {
    await salir();
    navigate("/ingresar", { replace: true });
  };

  const contenido = (
    <div className="mx-auto max-w-md">
      <div className="mb-6 flex flex-col items-center">
        <Avatar size="big">{usuario.iniciales}</Avatar>
        <div className="mt-3 text-lg font-extrabold text-slate-900">{usuario.nombre}</div>
        <p className="text-sm text-slate-500">{usuario.cargo || usuario.rol_display}</p>
        <span className="mt-2 badge badge-green">Activo</span>
      </div>
      <div className="content-card divide-y divide-slate-100 !p-0">
        <div className="profile-row"><span>Correo</span><b>{usuario.email || "—"}</b></div>
        <div className="profile-row"><span>Teléfono</span><b>{usuario.telefono || "—"}</b></div>
        <div className="profile-row"><span>Empresa</span><b>{usuario.empresa?.nombre}</b></div>
        {usuario.zona && <div className="profile-row"><span>Zona</span><b>{usuario.zona}</b></div>}
        <div className="profile-row"><span>Usuario</span><b>{usuario.username}</b></div>
      </div>
      {devuelta && (
        <Link to={`/tareas/${devuelta.id}/entregas`} className="mt-4 flex min-h-12 w-full items-center justify-between rounded-xl bg-white px-4 text-sm font-semibold text-slate-700 shadow-card">
          <span className="flex items-center gap-3"><Icon name="history" />Ver entrega devuelta</span><Icon name="chevron" size={17} />
        </Link>
      )}
      <button className="mt-3 flex min-h-12 w-full items-center justify-between rounded-xl border-0 bg-white px-4 text-sm font-semibold !text-red-600 shadow-card" onClick={cerrarSesion}>
        <span className="flex items-center gap-3"><Icon name="logout" />Cerrar sesión</span>
        <Icon name="chevron" size={17} />
      </button>
    </div>
  );

  if (admin) return (<><Heading title="Mi perfil" description="Datos de tu cuenta." />{contenido}</>);
  return (<><MobileHeader title="Mi perfil" /><div className="mobile-scroll px-5 pb-24 pt-6">{contenido}</div><BottomNav /></>);
}
