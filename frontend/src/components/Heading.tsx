import type { ReactNode } from "react";
import { hoyLargo } from "@/lib/formato";

export default function Heading({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="mb-1 text-xs font-semibold text-slate-400">{hoyLargo()}</p>
        <h1 className="text-[26px] font-extrabold tracking-tight text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  );
}
