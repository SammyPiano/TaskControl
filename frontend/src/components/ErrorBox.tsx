import Icon from "./Icon";

export default function ErrorBox({ mensajes }: { mensajes: string[] }) {
  if (!mensajes.length) return null;
  return (
    <div className="error-box" role="alert">
      <Icon name="alert" size={18} />
      <span>{mensajes.join(" ")}</span>
    </div>
  );
}
