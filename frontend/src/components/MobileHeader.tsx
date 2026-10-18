import type { ReactNode } from "react";
import Icon from "./Icon";

export default function MobileHeader({ title, back, action }: { title: string; back?: () => void; action?: ReactNode }) {
  return (
    <header className="mobile-header">
      <div className="w-11">{back && <button className="icon-button" onClick={back} aria-label="Volver"><Icon name="arrow" /></button>}</div>
      <h1 className="font-bold text-slate-900">{title}</h1>
      <div className="flex w-11 justify-end">{action}</div>
    </header>
  );
}
