import { useEffect, type ReactNode } from "react";

export default function Modal({ titulo, onCerrar, children }: { titulo: string; onCerrar: () => void; children: ReactNode }) {
  useEffect(() => {
    const cerrar = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    window.addEventListener("keydown", cerrar);
    return () => window.removeEventListener("keydown", cerrar);
  }, [onCerrar]);
  return (
    <div className="modal" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div className="modal-card" role="dialog" aria-modal="true" aria-label={titulo}>{children}</div>
    </div>
  );
}
