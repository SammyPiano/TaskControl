import { Link } from "react-router";
import Logo from "@/components/Logo";

export default function NoEncontrado() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-surface p-6 text-center">
      <Logo />
      <h1 className="text-xl font-extrabold text-slate-900">Página no encontrada</h1>
      <Link to="/" className="admin-primary">Ir al inicio</Link>
    </div>
  );
}
