export default function Progress({ value, label }: { value: number; label?: string }) {
  return (
    <div>
      {label && <div className="mb-2 flex justify-between text-xs font-semibold text-slate-500"><span>Lista de verificación</span><span>{label}</span></div>}
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-wine" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
