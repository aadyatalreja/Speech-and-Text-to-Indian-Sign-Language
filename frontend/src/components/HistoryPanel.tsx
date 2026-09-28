import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
export interface HistoryItem { text: string; ts: number }
const day = (ts: number) => { const d = Math.floor((new Date().setHours(0, 0, 0, 0) - new Date(ts).setHours(0, 0, 0, 0)) / 864e5); return d <= 0 ? "Today" : d === 1 ? "Yesterday" : "Earlier"; };

export default function HistoryDrawer({ open, items, onPick, onClear, onClose }: { open: boolean; items: HistoryItem[]; onPick: (t: string) => void; onClear: () => void; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  const groups = ["Today", "Yesterday", "Earlier"].map((g) => [g, items.filter((i) => day(i.ts) === g)] as const).filter(([, l]) => l.length);
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside role="dialog" aria-modal="true" aria-label="History" className="glass glass-strong fixed inset-y-3 right-3 z-50 flex w-[min(380px,calc(100vw-24px))] flex-col rounded-panel p-6"
            initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }} transition={{ duration: .22 }}>
            <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-semibold tracking-tight">Recent translations</h2>
              <button ref={closeRef} className="btn-quiet" onClick={onClose} aria-label="Close history">✕</button></div>
            <div className="flex-1 overflow-y-auto">
              {groups.length === 0 && <p className="text-sm text-muted">Nothing yet. Sentences you translate appear here.</p>}
              {groups.map(([g, list]) => (
                <div key={g} className="mb-5"><h3 className="mb-1 text-xs font-semibold text-muted">{g}</h3>
                  <ul>{list.map((h) => <li key={h.text}><button className="w-full rounded-ctl px-3 py-2 text-left hover:bg-accent-soft" onClick={() => { onPick(h.text); onClose(); }}>{h.text}</button></li>)}</ul></div>
              ))}
            </div>
            <button className="btn-quiet mt-3 self-start" onClick={onClear} disabled={!items.length}>Clear history</button>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}