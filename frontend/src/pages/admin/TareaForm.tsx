import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Field from "@/components/Field";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import SectionTitle from "@/components/SectionTitle";
import Switch from "@/components/Switch";
import { api, mensajesDe } from "@/lib/api";
import type { ItemPlantilla, Opcion, Persona, TareaDetalle, TipoServicio } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

type Opciones = { tipos: TipoServicio[]; empleados: Persona[]; prioridades: Opcion[] };
type Datos = {
  titulo: string; descripcion: string; tipo_servicio: string; prioridad: string; ubicacion: string;
  fecha_limite: string; asignado_a: string; criterios_aceptacion: string;
};
const VACIO: Datos = { titulo: "", descripcion: "", tipo_servicio: "", prioridad: "MEDIA", ubicacion: "", fecha_limite: "", asignado_a: "", criterios_aceptacion: "" };

/** Nueva tarea (con lista de verificación desde la plantilla) o edición de una tarea abierta. */
export default function TareaForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navigate = useNavigate();
  const { datos: opciones, errores: errOpciones } = useApi<Opciones>("tareas/opciones/");
  const { datos: tarea, errores: errTarea } = useApi<TareaDetalle>(editando ? `tareas/${id}/` : null);
  const [d, setD] = useState<Datos>(VACIO);
  const [items, setItems] = useState<ItemPlantilla[]>([]);
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!tarea) return;
    setD({
      titulo: tarea.titulo, descripcion: tarea.descripcion, tipo_servicio: String(tarea.tipo_servicio_id), prioridad: tarea.prioridad,
      ubicacion: tarea.ubicacion, fecha_limite: tarea.fecha_limite ?? "", asignado_a: String(tarea.asignado.id), criterios_aceptacion: tarea.criterios_aceptacion,
    });
  }, [tarea]);

  const set = (campo: keyof Datos) => (e: { target: { value: string } }) => setD({ ...d, [campo]: e.target.value });
  const tipo = opciones?.tipos.find((t) => String(t.id) === d.tipo_servicio);
  const elegirTipo = (valor: string) => {
    setD({ ...d, tipo_servicio: valor });
    const plantilla = opciones?.tipos.find((t) => String(t.id) === valor)?.plantilla;
    if (!editando) setItems(plantilla ? plantilla.items.map((i) => ({ descripcion: i.descripcion, obligatorio: i.obligatorio })) : []);
  };
  const cambiarItem = (i: number, cambio: Partial<ItemPlantilla>) => setItems(items.map((x, n) => (n === i ? { ...x, ...cambio } : x)));
  const mover = (i: number, paso: number) => {
    const nuevos = [...items];
    [nuevos[i], nuevos[i + paso]] = [nuevos[i + paso], nuevos[i]];
    setItems(nuevos);
  };

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    const cuerpo = { ...d, fecha_limite: d.fecha_limite || null, ...(editando ? {} : { items }) };
    try {
      const t = await api<TareaDetalle>(editando ? `tareas/${id}/` : "tareas/", { method: editando ? "PATCH" : "POST", body: cuerpo });
      navigate(`/tareas/${t.id}`, { replace: true });
    } catch (err) {
      setErrores(mensajesDe(err));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setEnviando(false);
    }
  };

  const cargandoTodo = !opciones || (editando && !tarea);
  return (
    <form onSubmit={enviar} noValidate>
      <Heading title={editando ? `Editar tarea · ${tarea?.codigo ?? ""}` : "Nueva tarea"} description={editando ? "Actualiza los datos o reasigna la orden de servicio." : "Completa los datos y asigna la orden de servicio."}>
        <Link className="admin-secondary" to={editando ? `/tareas/${id}` : "/tareas"}>Cancelar</Link>
        <button className="admin-primary" type="submit" disabled={enviando || cargandoTodo}><Icon name="check" size={17} />{enviando ? "Guardando…" : editando ? "Guardar cambios" : "Crear y asignar"}</button>
      </Heading>
      <ErrorBox mensajes={[...errOpciones, ...errTarea, ...errores]} />
      {errores.length > 0 && <div className="mb-4" />}
      {cargandoTodo && !errOpciones.length && <Cargando filas={4} />}
      {!cargandoTodo && (
        <div className="grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
          <section className="admin-card">
            <SectionTitle number="1" title="Información de la tarea" detail="Datos generales del servicio" />
            <div className="admin-form-grid">
              <Field wide label="Título de la tarea *"><input value={d.titulo} onChange={set("titulo")} maxLength={200} required placeholder="Ej.: Instalación de aire acondicionado split" /></Field>
              <Field wide label="Descripción"><textarea value={d.descripcion} onChange={set("descripcion")} placeholder="Qué se debe hacer y cualquier detalle útil para el técnico." /></Field>
              <Field label="Tipo de servicio *">
                <select value={d.tipo_servicio} onChange={(e) => elegirTipo(e.target.value)} required>
                  <option value="">Elige un servicio…</option>
                  {opciones.tipos.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                </select>
              </Field>
              <Field label="Prioridad *">
                <select value={d.prioridad} onChange={set("prioridad")}>{opciones.prioridades.map((p) => <option key={p.valor} value={p.valor}>{p.etiqueta}</option>)}</select>
              </Field>
              <Field wide label="Ubicación"><input value={d.ubicacion} onChange={set("ubicacion")} maxLength={255} placeholder="Cliente, dirección y sector" /></Field>
              <Field label="Fecha límite"><input type="date" value={d.fecha_limite} onChange={set("fecha_limite")} /></Field>
              <Field label="Empleado asignado *">
                <select value={d.asignado_a} onChange={set("asignado_a")} required>
                  <option value="">Elige un empleado…</option>
                  {opciones.empleados.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
                </select>
              </Field>
              <Field wide label="Criterios de aceptación"><textarea value={d.criterios_aceptacion} onChange={set("criterios_aceptacion")} placeholder="Uno por línea: qué debe cumplirse para aprobar la entrega." /></Field>
            </div>
          </section>
          <section className="admin-card self-start">
            {editando ? (
              <>
                <SectionTitle number="2" title="Lista de verificación" detail="Se definió al crear la tarea" />
                <div className="template-items">
                  {tarea!.items.map((x, i) => <div key={x.id}><span className="item-number">{i + 1}</span><span className="flex-1 text-[13px] text-slate-600">{x.descripcion}</span>{x.obligatorio && <small className="text-[11px] font-semibold text-wine">Obligatorio</small>}{x.completado && <Icon name="check" size={16} />}</div>)}
                  {!tarea!.items.length && <p className="text-xs text-slate-400">Sin lista de verificación.</p>}
                </div>
              </>
            ) : (
              <>
                <SectionTitle number="2" title="Lista de verificación" detail={tipo?.plantilla ? `Generada desde “${tipo.plantilla.nombre}”` : tipo ? "El servicio no tiene plantilla; agrega los ítems" : "Elige el tipo de servicio para cargar su plantilla"} />
                <div className="template-items">
                  {items.map((x, i) => (
                    <div key={i}>
                      <div className="orden-botones"><button type="button" onClick={() => mover(i, -1)} disabled={i === 0} aria-label="Subir"><Icon name="up" size={14} /></button><button type="button" onClick={() => mover(i, 1)} disabled={i === items.length - 1} aria-label="Bajar"><Icon name="down" size={14} /></button></div>
                      <span className="item-number">{i + 1}</span>
                      <input value={x.descripcion} onChange={(e) => cambiarItem(i, { descripcion: e.target.value })} aria-label={`Ítem ${i + 1}`} maxLength={255} />
                      <Switch checked={x.obligatorio} onChange={(v) => cambiarItem(i, { obligatorio: v })} />
                      <button type="button" onClick={() => setItems(items.filter((_, n) => n !== i))} aria-label={`Quitar ítem ${i + 1}`}><Icon name="trash" size={16} /></button>
                    </div>
                  ))}
                </div>
                <button type="button" className="add-item" onClick={() => setItems([...items, { descripcion: "", obligatorio: true }])}><Icon name="plus" size={16} />Agregar ítem</button>
              </>
            )}
          </section>
        </div>
      )}
    </form>
  );
}
