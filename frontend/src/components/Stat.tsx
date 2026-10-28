import { Link } from "react-router";
import Icon, { type IconName } from "./Icon";

export type Tono = "wine" | "amber" | "red" | "blue" | "slate";

/** Con `to`, la tarjeta es un acceso rápido a su sección. */
export default function Stat({ icon, label, value, detail, tone, to }: { icon: IconName; label: string; value: string; detail: string; tone: Tono; to?: string }) {
  const contenido = (
    <>
      <div className={`stat-icon ${tone}`}><Icon name={icon} /></div>
      <div className="min-w-0 flex-1">
        <p>{label}</p>
        <div className="mt-1 flex items-end gap-2"><b>{value}</b><span>{detail}</span></div>
      </div>
    </>
  );
  return to ? <Link to={to} className="stat-card stat-link" aria-label={`${label}: ${value}`}>{contenido}</Link> : <div className="stat-card">{contenido}</div>;
}
