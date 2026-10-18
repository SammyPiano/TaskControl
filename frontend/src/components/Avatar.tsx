import type { ReactNode } from "react";

export default function Avatar({ children, size }: { children: ReactNode; size?: "small" | "big" }) {
  return <div className={`avatar ${size ?? ""}`} aria-hidden="true">{children}</div>;
}
