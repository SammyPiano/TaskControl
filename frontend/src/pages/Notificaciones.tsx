import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";
import BottomNav from "@/components/BottomNav";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon, { type IconName } from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { api, mensajesDe, type Pagina } from "@/lib/api";
import { relativo } from "@/lib/formato";
import { rutaSpa } from "@/lib/navegacion";
import { esAdministrador, useSesion } from "@/lib/sesion";

type Notificacion = { id: number; mensaje: string; enlace: string; leida: boolean; creada_en: string };

/** Título e ícono según el aviso (el servidor solo guarda el mensaje). */
function tipo(mensaje: string): { icono: IconName; titulo: string } {
  const m = mensaje.toLowerCase();
  if (m.startsWith("nueva tarea")) return { icono: "tasks", titulo: "Nueva tarea asignada" };
  if (m.includes("entregó") || m.includes("para revisión")) return { icono: "review", titulo: "Entrega para revisión" };
  if (m.includes("fue devuelta")) return { icono: "alert", titulo: "Entrega devuelta" };
  if (m.includes("fue aprobada")) return { icono: "check", titulo: "Tarea completada" };
  if (m.includes("rechazad")) return { icono: "alert", titulo: m.startsWith("gasto") ? "Gasto rechazado" : "Viático rechazado" };
  if (m.includes("liquidado")) return { icono: "check", titulo: "Viático liquidado" };
  if (m.includes("autorizado")) return { icono: "wallet", titulo: "Viático autorizado" };
  if (m.includes("anticipo")) return { icono: "wallet", titulo: "Anticipo entregado" };
  if (m.includes("solicitó viático")) return { icono: "wallet", titulo: "Solicitud de viático" };
  if (m.includes("registró un gasto")) return { icono: "file", titulo: "Gasto registrado" };
  return { icono: "bell", titulo: "Aviso" };
}

export default function Notificaciones() {
  const { usuario, refrescar } = useSesion();
  const navigate = useNavigate();
  const admin = esAdministrador(usuario);
  const [lista, setLista] = useState<Notificacion[] | null>(null);
  const [siguiente, setSiguiente] = useState<number | null>(null);
  const [errores, setErrores] = useState<string[]>([]);

  const cargar = useCallback(async (pagina = 1) => {
    try {
      const datos = await api<Pagina<Notificacion>>(`notificaciones/?page=${pagina}`);
      setLista((previa) => (pagina === 1 ? datos.results : [...(previa ?? []), ...datos.results]));
      setSiguiente(datos.next ? pagina + 1 : null);
    } catch (e) {
      setErrores(mensajesDe(e, "No se pudieron cargar las notificaciones."));
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const abrir = async (n: Notificacion) => {
    if (!n.leida) {
      await api(`notificaciones/${n.id}/leer/`, { method: "POST" }).catch(() => null);
      setLista((l) => l?.map((x) => (x.id === n.id ? { ...x, leida: true } : x)) ?? null);
      refrescar();
    }
    const ruta = n.enlace && rutaSpa(n.enlace);
    if (ruta) navigate(ruta);
  };

  const leerTodas = async () => {
    await api("notificaciones/leer-todas/", { method: "POST" });
    setLista((l) => l?.map((x) => ({ ...x, leida: true })) ?? null);
    refrescar();
  };

  const hayNoLeidas = lista?.some((n) => !n.leida);
  const botonLeer = hayNoLeidas ? <button className="min-h-11 border-0 bg-transparent px-1 text-xs font-bold !text-wine" onClick={leerTodas} aria-label="Marcar todas como leídas">Leer</button> : undefined;

  const filas = (
    <>
      <ErrorBox mensajes={errores} />
      {!lista && !errores.length && <div className="p-5"><Cargando /></div>}
      {lista?.map((n) => {
        const t = tipo(n.mensaje);
        return (
          <button key={n.id} onClick={() => abrir(n)} className={`notification-row ${n.leida ? "" : "unread"}`}>
            <div className="round-icon"><Icon name={t.icono} size={19} /></div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-3"><b>{t.titulo}</b><small>{relativo(n.creada_en)}</small></div>
              <p>{n.mensaje}</p>
            </div>
            {!n.leida && <span className="unread-dot" aria-label="Sin leer" />}
          </button>
        );
      })}
      {lista && !lista.length && <div className="empty-state">No tienes notificaciones.</div>}
      {siguiente && <button className="secondary-button !rounded-none !border-x-0" onClick={() => cargar(siguiente)}>Cargar más</button>}
    </>
  );

  if (admin) {
    return (
      <>
        <Heading title="Notificaciones" description="Avisos de entregas, viáticos y gastos de tu empresa.">
          {hayNoLeidas && <button className="admin-secondary" onClick={leerTodas}><Icon name="check" size={17} />Marcar todas como leídas</button>}
        </Heading>
        <section className="admin-card !p-0">{filas}</section>
      </>
    );
  }
  return (
    <>
      <MobileHeader title="Notificaciones" action={botonLeer} />
      <div className="mobile-scroll pb-24 pt-3">
        <div className="px-5 py-2 text-xs font-bold uppercase tracking-wider text-slate-400">Recientes</div>
        {filas}
      </div>
      <BottomNav />
    </>
  );
}
