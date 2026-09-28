import { motion } from "framer-motion";
import type { Stage } from "../types/translation";
const STEPS = ["Understanding context", "Generating sign sequence", "Preparing output"];
const AT: Record<string, number> = { understanding: 0, representing: 1, preparing: 2, ready: 3 };
export default function ProcessingStatus({ stage }: { stage: Stage }) {
  const at = AT[stage] ?? 0;
  return (
    <div role="status" aria-live="polite" className="glass mx-auto max-w-md rounded-card p-6">
      <p className="mb-4 font-semibold">Understanding your sentence</p>
      <ul className="space-y-3">
        {STEPS.map((s, i) => (
          <li key={s} className={`flex items-center gap-3 text-sm ${i > at ? "text-muted" : "text-ink"}`}>
            {i < at ? <span className="grid h-5 w-5 place-items-center rounded-full bg-accent text-[11px] text-white" aria-label="done">✓</span>
              : i === at ? <motion.span className="h-5 w-5 rounded-full border-2 border-accent" animate={{ opacity: [1, .35, 1] }} transition={{ repeat: Infinity, duration: 1.4 }} aria-label="in progress" />
              : <span className="h-5 w-5 rounded-full border-2 border-black/15" aria-label="waiting" />}
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}
