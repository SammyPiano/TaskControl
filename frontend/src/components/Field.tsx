import type { ReactNode } from "react";

/** Campo del formulario de escritorio (admin-form-grid). */
export default function Field({ label, wide, children }: { label: string; wide?: boolean; children: ReactNode }) {
  return <label className={wide ? "col-span-2" : ""}><span>{label}</span>{children}</label>;
}
