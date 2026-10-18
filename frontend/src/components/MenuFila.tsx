import { useEffect, useRef, useState, type ReactNode } from "react";
import Icon from "./Icon";

/** Botón "⋯" con menú de acciones (tablas del administrador). */
export default function MenuFila({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const cerrar = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setAbierto(false);
    document.addEventListener("mousedown", cerrar);
    return () => document.removeEventListener("mousedown", cerrar);
  }, [abierto]);
  return (
    <div className="relative inline-block" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button className="icon-button" onClick={() => setAbierto(!abierto)} aria-label={etiqueta} aria-haspopup="menu" aria-expanded={abierto}><Icon name="more" size={17} /></button>
      {abierto && <div className="row-menu" role="menu" onClick={() => setAbierto(false)}>{children}</div>}
    </div>
  );
}
