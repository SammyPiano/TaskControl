/** Pie de tabla del diseño: "Mostrando 1–20 de 42 registros" y páginas. */
export default function Paginacion({ pagina, total, porPagina, onCambiar }: { pagina: number; total: number; porPagina: number; onCambiar: (p: number) => void }) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  const desde = total ? (pagina - 1) * porPagina + 1 : 0;
  const hasta = Math.min(pagina * porPagina, total);
  const inicio = Math.max(1, Math.min(pagina - 1, paginas - 2));
  const visibles = Array.from({ length: Math.min(3, paginas) }, (_, i) => inicio + i);
  return (
    <div className="table-footer">
      <span>Mostrando {desde}–{hasta} de {total} registros</span>
      <div>
        <button disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)}>Anterior</button>
        {visibles.map((p) => <button key={p} className={p === pagina ? "active" : ""} onClick={() => onCambiar(p)} aria-current={p === pagina ? "page" : undefined}>{p}</button>)}
        <button disabled={pagina >= paginas} onClick={() => onCambiar(pagina + 1)}>Siguiente</button>
      </div>
    </div>
  );
}
