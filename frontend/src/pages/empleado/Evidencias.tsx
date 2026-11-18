import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { api, mensajesDe } from "@/lib/api";
import { plural } from "@/lib/formato";
import type { TareaDetalle } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

const MAX_FOTOS = 10;
const MAX_BYTES = 10 * 1024 * 1024;
const TIPOS = ["image/jpeg", "image/png"];

type Foto = { archivo: File; url: string };

export default function Evidencias() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { datos: tarea, errores: errCarga } = useApi<TareaDetalle>(`tareas/${id}/`);
  const [fotos, setFotos] = useState<Foto[]>([]);
  const [comentario, setComentario] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const camara = useRef<HTMLInputElement>(null);
  const galeria = useRef<HTMLInputElement>(null);

  useEffect(() => () => fotos.forEach((f) => URL.revokeObjectURL(f.url)), [fotos]);

  /** Validación en el cliente (el servidor vuelve a validar y redimensiona a 1920 px). */
  const agregar = (lista: FileList | null) => {
    if (!lista) return;
    const nuevos: Foto[] = [];
    const problemas: string[] = [];
    for (const archivo of Array.from(lista)) {
      if (!TIPOS.includes(archivo.type)) problemas.push(`${archivo.name}: solo se permiten fotos JPG o PNG.`);
      else if (archivo.size > MAX_BYTES) problemas.push(`${archivo.name}: la foto supera los 10 MB.`);
      else nuevos.push({ archivo, url: URL.createObjectURL(archivo) });
    }
    const espacio = MAX_FOTOS - fotos.length;
    if (nuevos.length > espacio) problemas.push(`Puedes adjuntar hasta ${MAX_FOTOS} fotos por entrega.`);
    setFotos([...fotos, ...nuevos.slice(0, Math.max(0, espacio))]);
    setErrores(problemas);
  };
  const quitar = (i: number) => setFotos(fotos.filter((_, n) => n !== i));

  const pendientes = useMemo(() => tarea?.items.filter((i) => i.obligatorio && !i.completado) ?? [], [tarea]);
  const faltantes = [
    pendientes.length ? plural(pendientes.length, "ítem obligatorio", "ítems obligatorios") : "",
    fotos.length ? "" : "al menos 1 foto",
  ].filter(Boolean);

  const enviar = async () => {
    const datos = new FormData();
    fotos.forEach((f) => datos.append("fotos", f.archivo));
    datos.append("comentario", comentario.trim());
    setEnviando(true);
    try {
      await api(`tareas/${id}/entregas/`, { method: "POST", body: datos });
      navigate(`/tareas/${id}/entregas`, { replace: true, state: { enviada: true } });
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <MobileHeader title="Cargar evidencias" back={() => navigate(`/tareas/${id}`)} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <ErrorBox mensajes={errCarga} />
        {!tarea && !errCarga.length && <Cargando filas={3} alto="h-28" />}
        {tarea && (
          <>
            <div className="mb-5">
              <div className="text-base font-bold text-slate-900">{tarea.titulo}</div>
              <p className="mt-1 text-xs text-slate-500">Tarea #{tarea.codigo}{tarea.entregas.length > 0 && ` · Versión ${tarea.entregas[0].version + 1}`}</p>
            </div>
            <div className="detalle-grid">
              <div className="detalle-principal">
                <div className="mb-3 grid grid-cols-2 gap-3">
                  <button className="upload-button" onClick={() => camara.current?.click()} disabled={fotos.length >= MAX_FOTOS}>
                    <span className="round-icon !bg-wine !text-white"><Icon name="camera" /></span><span>Tomar foto</span><small>Usar cámara</small>
                  </button>
                  <button className="upload-button" onClick={() => galeria.current?.click()} disabled={fotos.length >= MAX_FOTOS}>
                    <span className="round-icon"><Icon name="image" /></span><span>Elegir foto</span><small>Desde galería</small>
                  </button>
                </div>
                <input ref={camara} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={(e) => { agregar(e.target.files); e.target.value = ""; }} />
                <input ref={galeria} type="file" accept="image/jpeg,image/png" multiple hidden onChange={(e) => { agregar(e.target.files); e.target.value = ""; }} />
                <p className="mb-4 text-xs text-slate-400">Máximo {MAX_FOTOS} archivos · JPG o PNG · 10 MB</p>

                <div className="section-title">Archivos adjuntos {fotos.length > 0 && <span className="font-normal text-slate-400">({fotos.length})</span>}</div>
                {fotos.length ? (
                  <div className="evidence-grid mb-5">
                    {fotos.map((f, i) => (
                      <div key={f.url} className="evidence-tile">
                        <img src={f.url} alt={`Evidencia ${i + 1}`} />
                        <div className="evidence-overlay"><span className="truncate">{f.archivo.name}</span><button onClick={() => quitar(i)} aria-label={`Quitar ${f.archivo.name}`}><Icon name="trash" size={17} /></button></div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mb-5 rounded-xl border border-dashed border-slate-300 p-7 text-center text-xs text-slate-400">Aún no hay archivos adjuntos</div>
                )}
              </div>

              <div className="detalle-lateral">
                <label className="field-label" htmlFor="comentario">Comentario para el administrador</label>
                <textarea id="comentario" className="textarea" value={comentario} onChange={(e) => setComentario(e.target.value)} placeholder="Describe el trabajo realizado o alguna observación importante..." />
                {faltantes.length > 0 && (
                  <div className="error-box mt-4" role="status"><Icon name="alert" size={18} /><span>{faltantes.length > 1 || pendientes.length > 1 ? "Faltan" : "Falta"} {faltantes.join(" y ")}.{pendientes.length > 0 && ` (${pendientes.map((p) => p.descripcion).join(", ")})`}</span></div>
                )}
                {errores.length > 0 && <div className="mt-3"><ErrorBox mensajes={errores} /></div>}
              </div>
            </div>
          </>
        )}
      </div>
      {tarea && (
        <div className="mobile-sticky-action">
          <button className="primary-button" onClick={enviar} disabled={enviando || !tarea.abierta || faltantes.length > 0}>{enviando ? "Enviando…" : "Solicitar revisión"}</button>
        </div>
      )}
    </>
  );
}
