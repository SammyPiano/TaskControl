export default function Switch({ checked, onChange, etiqueta = "Obligatorio" }: { checked: boolean; onChange: (v: boolean) => void; etiqueta?: string }) {
  return (
    <label className="mini-switch">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <i />
      <small>{etiqueta}</small>
    </label>
  );
}
