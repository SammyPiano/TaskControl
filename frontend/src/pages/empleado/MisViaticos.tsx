import { useState } from "react";
import { Link, useNavigate } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Icon from "@/components/Icon";
import MobileHeader from "@/components/MobileHeader";
import { query } from "@/lib/api";
import { plural, rd } from "@/lib/formato";
import type { EstadoViatico, ViaticoResumen } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

type Respuesta = { resultados: ViaticoResumen[]; resumen: { disponible: string; por_comprobar: string } };

const ESTADOS: { valor: EstadoViatico | ""; etiqueta: string }[] = [
  { valor: "", etiqueta: "Todos" },
  { valor: "SOLICITADO", etiqueta: "Solicitados" },
  { valor: "ANTICIPO_ENTREGADO", etiqueta: "Con anticipo" },
  { valor: "EN_COMPROBACION", etiqueta: "En comprobación" },
  { valor: "LIQUIDADO", etiqueta: "Liquidados" },
  { valor: "RECHAZADO", etiqueta: "Rechazados" },
];

export default function MisViaticos() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("");
  const [verFiltros, setVerFiltros] = useState(false);
  const { datos, errores, cargando } = useApi<Respuesta>(`viaticos/${query({ estado })}`);
  const lista = datos?.resultados;

  return (
    <>
      <MobileHeader title="Mis viáticos" action={<button className={`icon-button ${estado ? "!text-wine" : ""}`} onClick={() => setVerFiltros(!verFiltros)} aria-label="Filtrar" aria-expanded={verFiltros}><Icon name="filter" /></button>} />
      <div className="mobile-scroll px-5 pb-32 pt-5">
        {verFiltros && (
          <div className="chips chips-sangrado no-scrollbar mb-4">
            {ESTADOS.map((e) => <button key={e.valor} className={estado === e.valor ? "active" : ""} onClick={() => setEstado(e.valor)}>{e.etiqueta}</button>)}
          </div>
        )}
        <div className="expense-summary">
          <div><p>Disponible por gastar</p><b>{rd(datos?.resumen.disponible)}</b></div>
          <div><p>Anticipo por comprobar</p><b>{rd(datos?.resumen.por_comprobar)}</b></div>
        </div>
        <div className="mb-4 flex items-center justify-between"><div className="section-title !mb-0">Solicitudes recientes</div>{lista && <span className="text-xs text-slate-400">{plural(lista.length, "registro", "registros")}</span>}</div>
        <ErrorBox mensajes={errores} />
        {cargando && !lista && <Cargando filas={3} alto="h-28" />}
        <div className="lista-tarjetas">
          {lista?.map((v) => (
            <Link key={v.id} to={`/viaticos/${v.id}`} className="content-card expense-row">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0"><div className="text-sm font-bold text-slate-900">{v.concepto}</div><p className="mt-1 truncate text-xs text-slate-500">{v.tarea.codigo} · {v.tarea.titulo}</p></div>
                <Badge tipo="viatico" estado={v.estado}>{v.estado_display}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 border-t border-slate-100 pt-3">
                <div><small>Solicitado</small><b>{rd(v.monto_solicitado)}</b></div>
                <div><small>Aprobado</small><b>{v.monto_aprobado ? rd(v.monto_aprobado) : "—"}</b></div>
                <div><small>Anticipo</small><b>{rd(v.anticipo_entregado)}</b></div>
              </div>
            </Link>
          ))}
        </div>
        <div>
          {lista && !lista.length && <div className="rounded-xl border border-dashed border-slate-300 p-7 text-center text-xs text-slate-400">No tienes viáticos {estado ? "en este estado" : "registrados"}.</div>}
        </div>
      </div>
      <button className="fab" onClick={() => navigate("/viaticos/solicitar")}><Icon name="plus" />Solicitar viático</button>
    </>
  );
}
