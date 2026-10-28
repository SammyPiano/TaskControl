import { useEffect, useState } from "react";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import Switch from "@/components/Switch";
import { api, mensajesDe } from "@/lib/api";
import { plural } from "@/lib/formato";
import type { ItemPlantilla, TipoServicio } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

export default function Servicios() {
  const { datos: tipos, setDatos: setTipos, errores: errCarga } = useApi<TipoServicio[]>("servicios/");
  const [seleccion, setSeleccion] = useState<number | null>(null);
  const [items, setItems] = useState<ItemPlantilla[]>([]);
  const [nombre, setNombre] = useState("");
  const [nuevo, setNuevo] = useState<string | null>(null);
  const [errores, setErrores] = useState<string[]>([]);
  const [guardado, setGuardado] = useState(false);
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const tipo = tipos?.find((t) => t.id === seleccion) ?? null;
  useEffect(() => {
    if (tipos?.length && !tipo) setSeleccion(tipos[0].id);
  }, [tipos, tipo]);
  useEffect(() => {
    setItems(tipo?.plantilla?.items.map((i) => ({ ...i })) ?? []);
    setNombre(tipo?.nombre ?? "");
    setErrores([]);
    setGuardado(false);
  }, [tipo?.id]); // eslint-disable-line react-hooks/exhaustive-deps -- solo al cambiar de servicio, no al guardar

  const reemplazar = (t: TipoServicio) => setTipos((lista) => lista?.map((x) => (x.id === t.id ? t : x)) ?? null);
  const accion = async (fn: () => Promise<void>) => {
    setOcupado(true);
    try {
      await fn();
      setErrores([]);
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setOcupado(false);
    }
  };

  const guardar = () => accion(async () => {
    if (!tipo) return;
    if (nombre.trim() !== tipo.nombre) reemplazar(await api<TipoServicio>(`servicios/${tipo.id}/`, { method: "PATCH", body: { nombre } }));
    reemplazar(await api<TipoServicio>(`servicios/${tipo.id}/plantilla/`, { method: "PUT", body: { items } }));
    setGuardado(true);
  });
  const crear = () => accion(async () => {
    const t = await api<TipoServicio>("servicios/", { method: "POST", body: { nombre: nuevo } });
    setTipos((lista) => [...(lista ?? []), t].sort((a, b) => a.nombre.localeCompare(b.nombre)));
    setSeleccion(t.id);
    setNuevo(null);
    setAviso("");
  });
  const eliminar = () => accion(async () => {
    if (!tipo) return;
    const pregunta = tipo.usos
      ? `«${tipo.nombre}» tiene ${plural(tipo.usos, "tarea", "tareas")}. Se archivará: no aparecerá al crear tareas y las existentes no cambian. ¿Continuar?`
      : `¿Eliminar el servicio «${tipo.nombre}»?`;
    if (!window.confirm(pregunta)) return;
    const { archivado } = await api<{ archivado: boolean }>(`servicios/${tipo.id}/`, { method: "DELETE" });
    setAviso(archivado ? `«${tipo.nombre}» se archivó; sus tareas conservan el servicio. Créalo con el mismo nombre para reactivarlo.` : `«${tipo.nombre}» se eliminó.`);
    setTipos((lista) => lista?.filter((t) => t.id !== tipo.id) ?? null);
    setSeleccion(null);
  });
  const cambiar = (i: number, cambio: Partial<ItemPlantilla>) => { setItems(items.map((x, n) => (n === i ? { ...x, ...cambio } : x))); setGuardado(false); };
  const mover = (i: number, paso: number) => {
    const nuevos = [...items];
    [nuevos[i], nuevos[i + paso]] = [nuevos[i + paso], nuevos[i]];
    setItems(nuevos);
    setGuardado(false);
  };
  const activas = tipos?.filter((t) => t.plantilla).length ?? 0;

  return (
    <>
      <Heading title="Servicios y plantillas" description="Define listas reutilizables para cada tipo de servicio.">
        <button className="admin-primary" onClick={() => setNuevo("")}><Icon name="plus" size={17} />Nuevo servicio</button>
      </Heading>
      <ErrorBox mensajes={errCarga} />
      {aviso && <div className="success-banner"><Icon name="check" /><div><b>Servicio actualizado</b><span>{aviso}</span></div></div>}
      {!tipos && !errCarga.length && <Cargando filas={3} />}
      {tipos && (
        <div className="grid gap-5 lg:grid-cols-[.72fr_1.28fr]">
          <section className="admin-card self-start !p-0">
            <div className="card-heading px-5 py-4"><div><h2>Tipos de servicio</h2><p>{plural(activas, "plantilla activa", "plantillas activas")}</p></div></div>
            <div className="service-list">
              {nuevo !== null && (
                <div className="new-service">
                  <input autoFocus value={nuevo} onChange={(e) => setNuevo(e.target.value)} onKeyDown={(e) => e.key === "Enter" && crear()} placeholder="Nombre del servicio" aria-label="Nombre del nuevo servicio" />
                  <button className="admin-primary" onClick={crear} disabled={ocupado || !nuevo.trim()}>Crear</button>
                  <button className="admin-secondary" onClick={() => setNuevo(null)} aria-label="Cancelar"><Icon name="x" size={16} /></button>
                </div>
              )}
              {tipos.map((t) => (
                <button className={seleccion === t.id ? "active" : ""} onClick={() => setSeleccion(t.id)} key={t.id}>
                  <div className="stat-icon wine"><Icon name="briefcase" size={17} /></div>
                  <span><b>{t.nombre}</b><small>{plural(t.plantilla?.items.length ?? 0, "ítem", "ítems")} · {plural(t.usos, "uso", "usos")}</small></span>
                  <Icon name="chevron" size={16} />
                </button>
              ))}
              {!tipos.length && nuevo === null && <div className="empty-state">Crea tu primer tipo de servicio.</div>}
            </div>
          </section>
          {tipo && (
            <section className="admin-card self-start">
              <div className="card-heading mb-5">
                <div className="min-w-0"><h2>Plantilla · {tipo.nombre}</h2><p>Usa las flechas para cambiar el orden. Las tareas ya creadas no cambian.</p></div>
                <div className="flex gap-1">
                  <button onClick={eliminar} disabled={ocupado} className="!text-red-700">Eliminar</button>
                  <button onClick={guardar} disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar cambios"}</button>
                </div>
              </div>
              {errores.length > 0 && <div className="mb-4"><ErrorBox mensajes={errores} /></div>}
              {guardado && <div className="success-banner"><Icon name="check" /><div><b>Plantilla guardada</b><span>Se usará en las próximas tareas de «{tipo.nombre}».</span></div></div>}
              <div className="admin-form-grid mb-4"><label className="col-span-2"><span>Nombre del servicio</span><input value={nombre} onChange={(e) => { setNombre(e.target.value); setGuardado(false); }} /></label></div>
              <div className="template-editor">
                {items.map((x, i) => (
                  <div key={i}>
                    <div className="orden-botones"><button onClick={() => mover(i, -1)} disabled={i === 0} aria-label="Subir"><Icon name="up" size={14} /></button><button onClick={() => mover(i, 1)} disabled={i === items.length - 1} aria-label="Bajar"><Icon name="down" size={14} /></button></div>
                    <span>{i + 1}</span>
                    <input value={x.descripcion} onChange={(e) => cambiar(i, { descripcion: e.target.value })} aria-label={`Ítem ${i + 1}`} maxLength={255} />
                    <Switch checked={x.obligatorio} onChange={(v) => cambiar(i, { obligatorio: v })} />
                    <button onClick={() => { setItems(items.filter((_, n) => n !== i)); setGuardado(false); }} aria-label={`Quitar ítem ${i + 1}`}><Icon name="trash" size={16} /></button>
                  </div>
                ))}
                {!items.length && <p className="text-xs text-slate-400">Este servicio aún no tiene plantilla. Agrega los ítems de verificación.</p>}
              </div>
              <button className="add-item" onClick={() => { setItems([...items, { descripcion: "", obligatorio: true }]); setGuardado(false); }}><Icon name="plus" size={16} />Agregar ítem</button>
            </section>
          )}
        </div>
      )}
    </>
  );
}
