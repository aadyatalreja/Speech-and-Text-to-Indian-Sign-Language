import type { SignItem } from "../types/translation";
export default function GlossSequence({ items, activeIndex }: { items: SignItem[]; activeIndex: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-2" aria-label="Sign sequence">
      {items.map((s, i) => (
        <li key={i} className="flex items-center gap-2" aria-current={i === activeIndex ? "step" : undefined}>
          <span className={`rounded-lg border-2 px-3 py-1 font-bold ${i === activeIndex ? "border-ink bg-saffron" : s.available ? "border-ink bg-panel" : "border-dashed border-saffron-deep bg-panel text-saffron-deep"}`}>
            {s.gloss.replace("_", " ")}{!s.available && " ⚠"}
          </span>
          {i < items.length - 1 && <span aria-hidden>→</span>}
        </li>
      ))}
    </ol>
  );
}
