export default function SectionTitle({ number, title, detail }: { number: string; title: string; detail: string }) {
  return <div className="form-section-title"><span>{number}</span><div><b>{title}</b><small>{detail}</small></div></div>;
}
