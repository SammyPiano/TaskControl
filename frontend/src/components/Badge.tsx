import { claseEstado, type TipoEstado } from "@/lib/estados";

export default function Badge({ tipo, estado, children }: { tipo: TipoEstado; estado: string; children: string }) {
  return <span className={`badge ${claseEstado(tipo, estado)}`}>{children}</span>;
}
