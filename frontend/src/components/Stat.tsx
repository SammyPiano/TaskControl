import Icon, { type IconName } from "./Icon";

export type Tono = "wine" | "amber" | "red" | "blue" | "slate";

export default function Stat({ icon, label, value, detail, tone }: { icon: IconName; label: string; value: string; detail: string; tone: Tono }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}><Icon name={icon} /></div>
      <div className="min-w-0 flex-1">
        <p>{label}</p>
        <div className="mt-1 flex items-end gap-2"><b>{value}</b><span>{detail}</span></div>
      </div>
    </div>
  );
}
