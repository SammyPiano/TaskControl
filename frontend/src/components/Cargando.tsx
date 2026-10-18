export default function Cargando({ filas = 3, alto = "h-16" }: { filas?: number; alto?: string }) {
  return (
    <div className="space-y-3" role="status" aria-label="Cargando">
      {Array.from({ length: filas }, (_, i) => <div key={i} className={`skeleton ${alto}`} />)}
    </div>
  );
}
