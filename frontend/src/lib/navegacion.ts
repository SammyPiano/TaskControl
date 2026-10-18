import type { IconName } from "@/components/Icon";

export type ItemNav = { etiqueta: string; icon: IconName; to: string };

export const NAV_ADMIN: { titulo: string; items: ItemNav[] }[] = [
  {
    titulo: "Gestión",
    items: [
      { etiqueta: "Panel", icon: "grid", to: "/" },
      { etiqueta: "Tareas", icon: "tasks", to: "/tareas" },
      { etiqueta: "Entregas en revisión", icon: "review", to: "/entregas" },
      { etiqueta: "Viáticos", icon: "wallet", to: "/viaticos" },
    ],
  },
  {
    titulo: "Administración",
    items: [
      { etiqueta: "Usuarios", icon: "users", to: "/usuarios" },
      { etiqueta: "Servicios y plantillas", icon: "briefcase", to: "/servicios" },
      { etiqueta: "Reportes", icon: "chart", to: "/reportes" },
      { etiqueta: "Historial", icon: "history", to: "/historial" },
    ],
  },
];

export const NAV_EMPLEADO: ItemNav[] = [
  { etiqueta: "Tareas", icon: "tasks", to: "/" },
  { etiqueta: "Viáticos", icon: "wallet", to: "/viaticos" },
  { etiqueta: "Notificaciones", icon: "bell", to: "/notificaciones" },
  { etiqueta: "Perfil", icon: "user", to: "/perfil" },
];

/** Enlaces de notificaciones e historial ("/app/tareas/5") → ruta de React ("/tareas/5"). */
export function rutaSpa(enlace: string): string | null {
  return enlace.startsWith("/app/") ? enlace.slice(4) : null;
}
