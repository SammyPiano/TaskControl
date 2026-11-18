import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { api, mensajesDe } from "@/lib/api";
import type { Opcion, ViaticoDetalle } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

type Opciones = { tareas: { id: number; codigo: string; titulo: string }[]; categorias: Opcion[] };

export default function SolicitarViatico() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { datos: opciones, errores: errCarga } = useApi<Opciones>("viaticos/opciones/");
  const [tarea, setTarea] = useState(params.get("tarea") ?? "");
  const [concepto, setConcepto] = useState("");
  const [monto, setMonto] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);

  const enviar = async () => {
    setEnviando(true);
    try {
      const v = await api<ViaticoDetalle>("viaticos/", { method: "POST", body: { tarea, concepto, monto_solicitado: monto } });
      navigate(`/viaticos/${v.id}`, { replace: true });
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <MobileHeader title="Solicitar viático" back={() => navigate("/viaticos")} />
      <div className="mobile-scroll px-5 pb-28 pt-5">
        <div className="info-strip"><Icon name="wallet" /><div><b>El administrador autorizará el monto</b><span>Luego registra cada gasto con su comprobante.</span></div></div>
        <ErrorBox mensajes={errCarga} />
        <div className="form-grid">
          <div className="campo-ancho">
            <label className="field-label" htmlFor="tarea">Tarea</label>
            <select id="tarea" className="select" value={tarea} onChange={(e) => setTarea(e.target.value)}>
              <option value="">Elige una tarea…</option>
              {opciones?.tareas.map((t) => <option key={t.id} value={t.id}>{t.codigo} · {t.titulo}</option>)}
            </select>
          </div>
          <div className="campo-doble">
            <label className="field-label" htmlFor="concepto">Concepto</label>
            <div className="field"><Icon name="file" size={18} /><input id="concepto" value={concepto} onChange={(e) => setConcepto(e.target.value)} placeholder="Ej.: combustible y peajes" maxLength={255} /></div>
          </div>
          <div>
            <label className="field-label" htmlFor="monto">Monto solicitado</label>
            <div className="field amount-field"><b>RD$</b><input id="monto" inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value.replace(/[^\d.,]/g, ""))} placeholder="0.00" /></div>
          </div>
        </div>
        {errores.length > 0 && <div className="mt-4"><ErrorBox mensajes={errores} /></div>}
      </div>
      <div className="mobile-sticky-action">
        <button className="primary-button" onClick={enviar} disabled={enviando || !tarea || !concepto.trim() || !monto}>{enviando ? "Enviando…" : "Enviar solicitud"}</button>
      </div>
    </>
  );
}
