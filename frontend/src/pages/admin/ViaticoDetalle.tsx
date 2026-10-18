import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import Badge from "@/components/Badge";
import Cargando from "@/components/Cargando";
import ErrorBox from "@/components/ErrorBox";
import Field from "@/components/Field";
import Heading from "@/components/Heading";
import Icon from "@/components/Icon";
import Stat from "@/components/Stat";
import { api, mensajesDe } from "@/lib/api";
import { fecha, fechaHora, rd } from "@/lib/formato";
import type { ViaticoDetalle as Viatico } from "@/lib/tipos";
import { useApi } from "@/lib/useApi";

function Monto({ valor, onChange, id }: { valor: string; onChange: (v: string) => void; id: string }) {
  return <div className="amount-input"><b>RD$</b><input id={id} inputMode="decimal" value={valor} onChange={(e) => onChange(e.target.value.replace(/[^\d.,]/g, ""))} placeholder="0.00" /></div>;
}

export default function ViaticoDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { datos: v, setDatos, errores: errCarga } = useApi<Viatico>(`viaticos/${id}/`);
  const [aprobado, setAprobado] = useState<string | null>(null);
  const [anticipo, setAnticipo] = useState("");
  const [rechazando, setRechazando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [rechazoGasto, setRechazoGasto] = useState<number | null>(null);
  const [obsGasto, setObsGasto] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [ocupado, setOcupado] = useState(false);

  const ejecutar = async (ruta: string, body: object = {}) => {
    setOcupado(true);
    try {
      setDatos(await api<Viatico>(ruta, { method: "POST", body }));
      setErrores([]);
      setRechazando(false);
      setRechazoGasto(null);
      setObsGasto("");
      setAnticipo("");
    } catch (e) {
      setErrores(mensajesDe(e));
    } finally {
      setOcupado(false);
    }
  };

  const pendientes = v?.gastos.filter((g) => g.estado === "PENDIENTE").length ?? 0;
  const saldo = Number(v?.saldo ?? 0);
  const montoAprobado = aprobado ?? v?.monto_solicitado ?? "";

  return (
    <>
      <Heading title="Detalle y liquidación de viático" description={v ? `Solicitud ${v.codigo} · ${v.empleado.nombre} · Tarea ${v.tarea.codigo}` : "Cargando…"}>
        <button className="admin-secondary" onClick={() => navigate("/viaticos")}><Icon name="arrow" size={17} />Volver</button>
      </Heading>
      <ErrorBox mensajes={errCarga} />
      {!v && !errCarga.length && <Cargando filas={3} />}
      {v && (
        <>
          <div className="mb-5 grid gap-4 sm:grid-cols-3">
            <Stat icon="wallet" label="Solicitado" value={rd(v.monto_solicitado)} detail={fecha(v.solicitado_en)} tone="blue" />
            <Stat icon="check" label="Aprobado" value={v.monto_aprobado ? rd(v.monto_aprobado) : "—"} detail={v.autorizado_por ? `${v.estado === "RECHAZADO" ? "Rechazado" : "Autorizado"} por ${v.autorizado_por.nombre}` : "Por autorizar"} tone="wine" />
            <Stat icon="wallet" label="Anticipo" value={rd(v.anticipo_entregado)} detail={Number(v.anticipo_entregado) > 0 ? "Entregado" : "Sin anticipo"} tone="amber" />
          </div>

          <div className="mb-5 flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <Badge tipo="viatico" estado={v.estado}>{v.estado_display}</Badge>
            <b className="text-slate-800">{v.concepto}</b>·
            <Link className="font-semibold text-wine" to={`/tareas/${v.tarea.id}`}>{v.tarea.codigo} · {v.tarea.titulo}</Link>
            <Link className="ml-auto text-xs font-semibold text-wine" to={`/historial?entidad=viatico&entidad_id=${v.id}`}>Ver historial</Link>
          </div>
          {errores.length > 0 && <div className="mb-4"><ErrorBox mensajes={errores} /></div>}

          {v.estado === "SOLICITADO" && (
            <div className="action-card mb-5">
              <h2>Autorizar solicitud</h2>
              <p className="ayuda">El anticipo es opcional y no puede superar el monto aprobado.</p>
              <div className="admin-form-grid mt-4">
                <Field label="Monto aprobado *"><Monto id="aprobado" valor={montoAprobado} onChange={setAprobado} /></Field>
                <Field label="Anticipo a entregar"><Monto id="anticipo" valor={anticipo} onChange={setAnticipo} /></Field>
              </div>
              {Number(anticipo || 0) > Number(montoAprobado || 0) && <p className="mt-2 text-xs font-semibold text-red-700">El anticipo no puede superar el monto aprobado.</p>}
              <div className="mt-4 flex flex-wrap justify-end gap-2">
                <button className="admin-secondary !text-red-700" onClick={() => setRechazando(true)} disabled={ocupado}><Icon name="x" size={17} />Rechazar</button>
                <button className="admin-primary" disabled={ocupado || !montoAprobado || Number(anticipo || 0) > Number(montoAprobado)} onClick={() => ejecutar(`viaticos/${id}/autorizar/`, { monto_aprobado: montoAprobado.replace(/,/g, ""), anticipo: anticipo.replace(/,/g, "") })}><Icon name="check" size={17} />Autorizar</button>
              </div>
              {rechazando && (
                <div className="return-box rechazo-box">
                  <label htmlFor="motivo">Motivo del rechazo *</label>
                  <textarea id="motivo" autoFocus value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Explica al empleado por qué no procede..." />
                  <div><button onClick={() => setRechazando(false)}>Cancelar</button><button disabled={ocupado || !motivo.trim()} onClick={() => ejecutar(`viaticos/${id}/rechazar/`, { observacion: motivo })}>Confirmar rechazo</button></div>
                </div>
              )}
            </div>
          )}
          {v.estado === "RECHAZADO" && <div className="error-box mb-5"><Icon name="alert" size={18} /><span>Rechazado: {v.observacion}</span></div>}
          {v.estado === "AUTORIZADO" && (
            <div className="action-card mb-5">
              <h2>Entregar anticipo</h2>
              <p className="ayuda">Máximo {rd(v.monto_aprobado)}. También puedes esperar a que el empleado registre sus gastos.</p>
              <div className="mt-4 flex flex-wrap items-end gap-3">
                <div className="admin-form-grid flex-1"><Field label="Anticipo *"><Monto id="anticipo2" valor={anticipo} onChange={setAnticipo} /></Field></div>
                <button className="admin-primary" disabled={ocupado || !anticipo} onClick={() => ejecutar(`viaticos/${id}/anticipo/`, { anticipo: anticipo.replace(/,/g, "") })}><Icon name="wallet" size={17} />Registrar anticipo</button>
              </div>
            </div>
          )}

          <section className="admin-card !p-0">
            <div className="card-heading px-5 py-4">
              <div><h2>Gastos reportados</h2><p>Revisa cada comprobante</p></div>
              {v.gastos.length > 0 && <span className={`badge ${pendientes ? "badge-amber" : "badge-green"}`}>{pendientes ? "Pendientes por revisar" : "Todos revisados"}</span>}
            </div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Comprobante</th><th>Categoría</th><th>Fecha</th><th>Detalle</th><th>Monto</th><th>Estado</th><th>Validación</th></tr></thead>
                <tbody>
                  {v.gastos.map((g) => (
                    <tr key={g.id}>
                      <td><a className="receipt-thumb" href={g.comprobante} target="_blank" rel="noreferrer" aria-label="Ver comprobante"><Icon name="file" size={17} /></a></td>
                      <td><b>{g.categoria_display}</b></td>
                      <td>{fecha(g.fecha)}</td>
                      <td className="!whitespace-normal">{g.descripcion || "—"}{g.observacion && <small className="block text-red-700">{g.observacion}</small>}</td>
                      <td><b>{rd(g.monto)}</b></td>
                      <td><Badge tipo="gasto" estado={g.estado}>{g.estado_display}</Badge></td>
                      <td>
                        {g.estado === "PENDIENTE" && v.estado === "EN_COMPROBACION" ? (
                          rechazoGasto === g.id ? (
                            <div className="flex items-center gap-2">
                              <input className="h-8 w-44 rounded-md border border-red-200 px-2 text-xs" autoFocus value={obsGasto} onChange={(e) => setObsGasto(e.target.value)} placeholder="Motivo del rechazo *" aria-label="Motivo del rechazo" />
                              <div className="expense-actions">
                                <button disabled={ocupado || !obsGasto.trim()} onClick={() => ejecutar(`gastos/${g.id}/rechazar/`, { observacion: obsGasto })}><Icon name="x" size={15} />Confirmar</button>
                                <button onClick={() => setRechazoGasto(null)}>Cancelar</button>
                              </div>
                            </div>
                          ) : (
                            <div className="expense-actions">
                              <button disabled={ocupado} onClick={() => ejecutar(`gastos/${g.id}/aprobar/`)}><Icon name="check" size={15} />Aprobar</button>
                              <button disabled={ocupado} onClick={() => { setRechazoGasto(g.id); setObsGasto(""); }}><Icon name="x" size={15} />Rechazar</button>
                            </div>
                          )
                        ) : <span className="text-slate-400">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!v.gastos.length && <div className="empty-state">El empleado aún no registra gastos.</div>}
            </div>
          </section>

          {v.liquidacion ? (
            <div className="settlement-box liquidado">
              <div>
                <span>Liquidación</span>
                <p><b>Gastos aprobados {rd(v.liquidacion.total_gastos)}</b><i>−</i><b>Anticipo {rd(v.liquidacion.total_anticipo)}</b><i>=</i><strong>Saldo {rd(Math.abs(Number(v.liquidacion.saldo)))}</strong></p>
                <small>{v.liquidacion.resultado_display} · {v.liquidacion.liquidado_por} · {fechaHora(v.liquidacion.liquidada_en)}</small>
              </div>
              <span className="badge badge-green">Liquidado</span>
            </div>
          ) : v.admite_gastos && (
            <div className="settlement-box">
              <div>
                <span>Liquidación</span>
                <p><b>Gastos aprobados {rd(v.totales.aprobado)}</b><i>−</i><b>Anticipo {rd(v.anticipo_entregado)}</b><i>=</i><strong>Saldo {rd(Math.abs(saldo))}</strong></p>
                <small className={saldo < 0 ? "!text-orange-700" : ""}>{v.resultado_previsto}</small>
              </div>
              <button disabled={pendientes > 0 || ocupado} onClick={() => ejecutar(`viaticos/${id}/liquidar/`)}><Icon name="check" size={17} />{pendientes ? "Liquidar · gastos pendientes" : "Liquidar viático"}</button>
            </div>
          )}
        </>
      )}
    </>
  );
}
