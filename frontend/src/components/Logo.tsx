export default function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="logo-mark"><span /><span /><span /></div>
      {!compact && <div className="text-[19px] font-extrabold tracking-tight text-slate-900">Task<span className="text-wine">Control</span></div>}
    </div>
  );
}
