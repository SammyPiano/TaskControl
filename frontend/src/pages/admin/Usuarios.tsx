import { useState, type FormEvent } from "react";
import Avatar from "@/components/Avatar";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Field from "@/components/Field";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import MenuFila from "@/components/MenuFila";
import Modal from "@/components/Modal";
import SectionTitle from "@/components/SectionTitle";
import { api, mensajesDe, query } from "@/lib/api";
import { useSesion } from "@/lib/sesion";
import { useApi } from "@/lib/useApi";

type Usuario = {
  id: number; username: string; first_name: string; last_name: string; nombre: string; iniciales: string; email: string;
  rol: "EMPLEADO" | "ADMINISTRADOR"; rol_display: string; cargo: string; telefono: string; zona: string; is_active: boolean; tareas_activas: number;
};
type Formulario = Omit<Usuario, "id" | "nombre" | "iniciales" | "rol_display" | "tareas_activas" | "is_active"> & { password: string };
const VACIO: Formulario = { username: "", first_name: "", last_name: "", email: "", rol: "EMPLEADO", cargo: "", telefono: "", zona: "", password: "" };

function FormUsuario({ usuario, onCerrar, onGuardado }: { usuario: Usuario | null; onCerrar: () => void; onGuardado: () => void }) {
  const [d, setD] = useState<Formulario>(usuario ? { ...usuario, password: "" } : VACIO);
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const set = (campo: keyof Formulario) => (e: { target: { value: string } }) => setD({ ...d, [campo]: e.target.value });

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const cuerpo = usuario && !d.password ? { ...d, password: undefined } : d;
      await api(usuario ? `usuarios/${usuario.id}/` : "usuarios/", { method: usuario ? "PATCH" : "POST", body: cuerpo });
      onGuardado();
    } catch (err) {
      setErrores(mensajesDe(err));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal titulo={usuario ? "Editar usuario" : "Nuevo usuario"} onCerrar={onCerrar}>
      <form onSubmit={enviar} noValidate>
        <SectionTitle number={usuario ? "✎" : "+"} title={usuario ? "Editar usuario" : "Nuevo usuario"} detail="Pertenece a tu empresa; el rol define a qué pantallas accede" />
        <ErrorBox mensajes={errores} />
        {errores.length > 0 && <div className="mb-4" />}
        <div className="admin-form-grid">
          <Field label="Nombre *"><input value={d.first_name} onChange={set("first_name")} autoFocus /></Field>
          <Field label="Apellido"><input value={d.last_name} onChange={set("last_name")} /></Field>
          <Field label="Usuario *"><input value={d.username} onChange={set("username")} autoCapitalize="none" /></Field>
          <Field label="Correo electrónico"><input type="email" value={d.email} onChange={set("email")} /></Field>
          <Field label="Rol *"><select value={d.rol} onChange={set("rol")}><option value="EMPLEADO">Empleado de campo</option><option value="ADMINISTRADOR">Administrador</option></select></Field>
          <Field label="Cargo"><input value={d.cargo} onChange={set("cargo")} placeholder="Técnico de mantenimiento" /></Field>
          <Field label="Teléfono"><input type="tel" value={d.telefono} onChange={set("telefono")} placeholder="(809) 555-0148" /></Field>
          <Field label="Zona"><input value={d.zona} onChange={set("zona")} placeholder="Santo Domingo Este" /></Field>
          <Field wide label={usuario ? "Nueva contraseña (opcional)" : "Contraseña inicial *"}><input type="password" value={d.password} onChange={set("password")} autoComplete="new-password" /></Field>
        </div>
        <div className="modal-actions">
          <button type="button" className="admin-secondary" onClick={onCerrar}>Cancelar</button>
          <button type="submit" className="admin-primary" disabled={enviando}><Icon name="check" size={17} />{enviando ? "Guardando…" : "Guardar"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Usuarios() {
  const { usuario: yo } = useSesion();
  const [q, setQ] = useState("");
  const [rol, setRol] = useState("");
  const [estado, setEstado] = useState("");
  const { datos, errores, setErrores, recargar } = useApi<Usuario[]>(`usuarios/${query({ q, rol, estado })}`);
  const [editando, setEditando] = useState<Usuario | null | undefined>(undefined);

  const alternar = async (u: Usuario) => {
    try {
      await api(`usuarios/${u.id}/`, { method: "PATCH", body: { is_active: !u.is_active } });
      recargar();
    } catch (e) {
      setErrores(mensajesDe(e));
    }
  };

  return (
    <>
      <Heading title="Usuarios" description="Administra empleados, administradores y accesos.">
        <button className="admin-primary" onClick={() => setEditando(null)}><Icon name="plus" size={17} />Nuevo usuario</button>
      </Heading>
      <section className="admin-card !p-0">
        <div className="filters-row">
          <div className="filter-search"><Icon name="search" size={17} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por nombre, correo o zona..." aria-label="Buscar" /></div>
          <select value={rol} onChange={(e) => setRol(e.target.value)} aria-label="Rol"><option value="">Todos los roles</option><option value="EMPLEADO">Empleados</option><option value="ADMINISTRADOR">Administradores</option></select>
          <select value={estado} onChange={(e) => setEstado(e.target.value)} aria-label="Estado"><option value="">Todos los estados</option><option value="activo">Activos</option><option value="inactivo">Inactivos</option></select>
        </div>
        <ErrorBox mensajes={errores} />
        {!datos && !errores.length && <div className="p-5"><Cargando filas={4} alto="h-12" /></div>}
        {datos && (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Usuario</th><th>Rol</th><th>Zona</th><th>Tareas activas</th><th>Estado</th><th>Acciones</th></tr></thead>
              <tbody>
                {datos.map((u) => (
                  <tr key={u.id}>
                    <td><div className="flex items-center gap-3"><Avatar>{u.iniciales}</Avatar><div><b className="block text-slate-800">{u.nombre}</b><small className="text-slate-400">{u.email || u.username}</small></div></div></td>
                    <td>{u.cargo || (u.rol === "EMPLEADO" ? "Empleado de campo" : "Administrador")}{u.cargo && <small className="block text-slate-400">{u.rol_display}</small>}</td>
                    <td>{u.zona || "—"}</td>
                    <td>{u.tareas_activas}</td>
                    <td><span className={`badge ${u.is_active ? "badge-green" : "badge-neutral"}`}>{u.is_active ? "Activo" : "Inactivo"}</span></td>
                    <td>
                      <MenuFila etiqueta={`Acciones de ${u.nombre}`}>
                        <button role="menuitem" onClick={() => setEditando(u)}><Icon name="edit" size={17} />Editar</button>
                        {u.id !== yo?.id && <button role="menuitem" onClick={() => alternar(u)}><Icon name={u.is_active ? "x" : "check"} size={17} />{u.is_active ? "Desactivar" : "Activar"}</button>}
                      </MenuFila>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!datos.length && <div className="empty-state">No hay usuarios con estos filtros.</div>}
          </div>
        )}
      </section>
      {editando !== undefined && <FormUsuario usuario={editando} onCerrar={() => setEditando(undefined)} onGuardado={() => { setEditando(undefined); recargar(); }} />}
    </>
  );
}
