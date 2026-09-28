import type { ReactNode } from "react";

export const GlassCard = ({ children, className = "", strong = false, ...r }: { children: ReactNode; className?: string; strong?: boolean } & React.HTMLAttributes<HTMLElement>) =>
  <section {...r} className={`glass ${strong ? "glass-strong" : ""} rounded-panel ${className}`}>{children}</section>;

export const SectionHeader = ({ title, aside }: { title: string; aside?: ReactNode }) =>
  <div className="mb-4 flex items-center justify-between gap-3"><h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>{aside}</div>;

export function SegmentedControl<T extends string | number>({ label, value, options, onChange, disabled = [] }:
  { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; disabled?: T[] }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-ctl bg-line/[.07] p-1">
      {options.map((o) => (
        <button key={String(o.value)} role="radio" aria-checked={value === o.value} disabled={disabled.includes(o.value)} onClick={() => onChange(o.value)}
          className={`rounded-[9px] px-3.5 py-1.5 text-sm font-semibold transition disabled:opacity-40 ${value === o.value ? "bg-raised text-ink shadow-sm ring-1 ring-line/5" : "text-muted hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export const StatusIndicator = ({ ok, label }: { ok: boolean | null; label: string }) => (
  <span className="inline-flex items-center gap-2 text-sm font-medium text-muted" role="status">
    <span className={`h-2 w-2 rounded-full ${ok === null ? "bg-line/30" : ok ? "bg-emerald-500" : "bg-amber-500"}`} aria-hidden />{label}
  </span>
);