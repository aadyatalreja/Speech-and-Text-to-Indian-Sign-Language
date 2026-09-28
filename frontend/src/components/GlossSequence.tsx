import { motion } from "framer-motion";
import type { SignItem } from "../types/translation";
export default function GlossSequence({ items, activeIndex }: { items: SignItem[]; activeIndex: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-2" aria-label="Sign sequence">
      {items.map((s, i) => (
        <motion.li key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.2 }}
          aria-current={i === activeIndex ? "step" : undefined} className="flex items-center gap-2">
          <span className={`rounded-ctl px-3 py-1.5 text-sm font-semibold ${i === activeIndex ? "bg-accent text-white" : s.available ? "bg-white/80 ring-1 ring-black/10" : "bg-warn-soft text-warn ring-1 ring-warn/30"}`}>
            {s.gloss.replace("_", " ")}{!s.available && " ⚠"}
          </span>
          {i < items.length - 1 && <span className="text-muted" aria-hidden>→</span>}
        </motion.li>
      ))}
    </ol>
  );
}
