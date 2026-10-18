import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { api, mensajesDe } from "@/lib/api";
import { hoyIso, rd, tamano } from "@/lib/formato";
import type { Opcion, ViaticoDetalle } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

const MAX_BYTES = 10 * 1024 * 1024;

export default function RegistrarGasto() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { datos: v, errores: errCarga } = useApi<ViaticoDetalle>(`viaticos/${id}/`);
  const { datos: opciones } = useApi<{ categorias: Opcion[] }>("viaticos/opciones/");
  const [categoria, setCategoria] = useState("TRANSPORTE");
  const [fechaGasto, setFechaGasto] = useState(hoyIso());
  const [monto, setMonto] = useState("");
  const [nota, setNota] = useState("");
  const [comprobante, setComprobante] = useState<File | null>(null);
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (v && !v.admite_gastos) navigate(`/viaticos/${id}`, { replace: true });
  }, [v, id, navigate]);

  const elegir = (archivo: File | undefined) => {
    if (!archivo) return;
    if (!["image/jpeg", "image/png"].includes(archivo.type)) return setErrores(["El comprobante debe ser una foto JPG o PNG."]);
    if (archivo.size > MAX_BYTES) return setErrores(["La foto supera los 10 MB."]);
    setErrores([]);
    setComprobante(archivo);
  };

  const enviar = async () => {
    if (!comprobante) return;
    const datos = new FormData();
    datos.append("categoria", categoria);
    datos.append("fecha", fechaGasto);
    datos.append("monto", monto.replace(/,/g, ""));
    datos.append("descripcion", nota.trim());
    datos.append("comprobante", comprobante);
    setEnviando(true);
    try {
      await api(`viaticos/${id}/gastos/`, { method: "POST", body: datos });
      navigate(`/viaticos/${id}`, { replace: true });
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setEnviando(false);
    }
  };

  // Con anticipo: lo que falta por comprobar; sin anticipo: lo aprobado que aún no cubren los gastos
  const conAnticipo = Number(v?.anticipo_entregado ?? 0) > 0;
  const base = Number((conAnticipo ? v?.anticipo_entregado : v?.monto_aprobado) ?? 0);
  const disponible = v ? Math.max(base - Number(v.totales.aprobado) - Number(v.totales.pendiente), 0) : 0;

  return (
    <>
      <MobileHeader title="Registrar gasto" back={() => navigate(`/viaticos/${id}`)} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <ErrorBox mensajes={errCarga} />
        {v && <div className="info-strip"><Icon name="wallet" /><div><b>{conAnticipo ? "Anticipo disponible" : "Aprobado disponible"}: {rd(disponible)}</b><span>{v.concepto} · {v.tarea.codigo}</span></div></div>}
        <label className="field-label" htmlFor="categoria">Categoría</label>
        <select id="categoria" className="select" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          {(opciones?.categorias ?? [{ valor: "TRANSPORTE", etiqueta: "Transporte" }]).map((c) => <option key={c.valor} value={c.valor}>{c.etiqueta}</option>)}
        </select>
        <label className="field-label mt-5" htmlFor="fecha">Fecha del gasto</label>
        <div className="field mobile-field-date"><Icon name="calendar" size={18} /><input id="fecha" type="date" max={hoyIso()} value={fechaGasto} onChange={(e) => setFechaGasto(e.target.value)} /></div>
        <label className="field-label mt-5" htmlFor="monto">Monto</label>
        <div className="field amount-field"><b>RD$</b><input id="monto" inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value.replace(/[^\d.,]/g, ""))} placeholder="0.00" /></div>
        <label className="field-label mt-5">Comprobante</label>
        <input ref={entrada} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={(e) => { elegir(e.target.files?.[0]); e.target.value = ""; }} />
        {!comprobante ? (
          <button className="receipt-upload" onClick={() => entrada.current?.click()}><div className="round-icon"><Icon name="camera" /></div><b>Adjuntar foto del comprobante</b><span>JPG o PNG · Máximo 10 MB</span></button>
        ) : (
          <div className="file-row">
            <div className="round-icon"><Icon name="file" /></div>
            <div className="min-w-0 flex-1"><b className="truncate">{comprobante.name}</b><span>{tamano(comprobante.size)} · Archivo listo</span></div>
            <button className="icon-button" onClick={() => setComprobante(null)} aria-label="Quitar comprobante"><Icon name="x" /></button>
          </div>
        )}
        <label className="field-label mt-5" htmlFor="nota">Nota <span className="font-normal text-slate-400">(opcional)</span></label>
        <textarea id="nota" className="textarea" value={nota} onChange={(e) => setNota(e.target.value)} maxLength={255} placeholder="Agrega un detalle sobre este gasto..." />
        {errores.length > 0 && <div className="mt-4"><ErrorBox mensajes={errores} /></div>}
      </div>
      <div className="mobile-sticky-action">
        <button className="primary-button" onClick={enviar} disabled={enviando || !comprobante || !monto || !fechaGasto}>{enviando ? "Enviando…" : "Enviar a comprobación"}</button>
      </div>
    </>
  );
}
