import { clasePrioridad } from "@/lib/estados";

export default function Prioridad({ valor, children }: { valor: string; children: string }) {
  return <span className={clasePrioridad(valor)}>{children}</span>;
}
