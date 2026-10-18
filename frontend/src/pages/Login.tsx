import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import Logo from "@/components/Logo";
import { mensajesDe } from "@/lib/api";
import { useSesion } from "@/lib/sesion";

export default function Login() {
  const { usuario, ingresar } = useSesion();
  const navigate = useNavigate();
  const desde = (useLocation().state as { desde?: string } | null)?.desde ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [verClave, setVerClave] = useState(false);
  const [olvido, setOlvido] = useState(false);
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to={desde} replace />;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErrores([]);
    setEnviando(true);
    try {
      await ingresar(username.trim(), password);
      navigate(desde, { replace: true });
    } catch (err) {
      setErrores(mensajesDe(err, "No se pudo conectar con el servidor."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="login-screen bg-surface">
      <form onSubmit={enviar} className="mx-auto flex min-h-dvh max-w-[390px] flex-col bg-white px-6 pb-8 pt-16" noValidate>
        <div className="mx-auto mb-12"><Logo /></div>
        <div className="mb-8">
          <h1 className="mb-2 text-2xl font-extrabold tracking-tight text-slate-900">Bienvenido de nuevo</h1>
          <p className="text-sm leading-relaxed text-slate-500">Ingresa a tu cuenta para gestionar tus tareas de hoy.</p>
        </div>

        <label className="field-label" htmlFor="usuario">Correo electrónico</label>
        <div className="field mb-5">
          <Icon name="user" size={18} />
          <input id="usuario" type="text" inputMode="email" autoComplete="username" autoCapitalize="none" autoFocus required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="nombre@empresa.com" />
        </div>

        <label className="field-label" htmlFor="clave">Contraseña</label>
        <div className="field">
          <Icon name="file" size={18} />
          <input id="clave" type={verClave ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="button" className="min-h-11 border-0 bg-transparent px-1 text-xs font-semibold !text-wine" onClick={() => setVerClave(!verClave)} aria-pressed={verClave}>
            {verClave ? "Ocultar" : "Ver"}
          </button>
        </div>
        <button type="button" className="mb-8 mt-3 min-h-11 self-end border-0 bg-transparent text-sm font-semibold !text-wine" onClick={() => setOlvido(!olvido)}>¿Olvidaste tu contraseña?</button>
        {olvido && <p className="-mt-6 mb-6 rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">Pide al administrador de tu empresa que restablezca tu contraseña desde Usuarios.</p>}

        {errores.length > 0 && <div className="mb-5"><ErrorBox mensajes={errores} /></div>}
        <button className="primary-button" type="submit" disabled={enviando || !username || !password}>{enviando ? "Ingresando…" : "Iniciar sesión"}</button>

        <div className="mt-auto pt-10 text-center text-xs leading-relaxed text-slate-400">TaskControl · Gestión de servicios de campo<br />República Dominicana</div>
      </form>
    </div>
  );
}
