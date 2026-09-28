import type { SignAnimationController, SignItem } from "../types/translation";
import { SegmentedControl } from "./ui";
interface Props { items: SignItem[]; index: number; progress: number; playing: boolean; speed: number; c: SignAnimationController }
const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function SignPlayer({ items, index, progress, playing, speed, c }: Props) {
  const len = (i: SignItem) => (i.duration + i.pause_after) / speed;
  const total = items.reduce((a, i) => a + len(i), 0);
  const done = index < 0 ? 0 : items.slice(0, index).reduce((a, i) => a + len(i), 0) + (items[index] ? progress * len(items[index]) : 0);
  const pct = total ? Math.round((done / total) * 100) : 0;
  const state = playing ? "Playing" : index < 0 ? "Ready" : pct >= 100 ? "Finished" : "Paused";
  return (
    <div className="mt-5">
      <p className="text-center text-xs text-muted">Current sign</p>
      <p aria-live="polite" className="text-center text-lg font-bold">{index >= 0 && items[index] ? items[index].gloss.replace("_", " ") : "—"}</p>

      <ol className="mt-4 flex items-center gap-1 overflow-x-auto pb-1" aria-label="Sign timeline">
        {items.map((s, i) => (
          <li key={i} className="flex flex-1 items-center gap-1 last:flex-none" aria-current={i === index ? "step" : undefined}>
            <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold transition ${i === index ? "bg-accent text-white shadow-glow" : i < index ? "text-ink" : "text-muted"} ${!s.available ? "line-through decoration-warn" : ""}`}>{s.gloss.replace("_", " ")}</span>
            {i < items.length - 1 && <span className={`h-px min-w-3 flex-1 ${i < index ? "bg-accent" : "bg-line/20"}`} aria-hidden />}
          </li>
        ))}
      </ol>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-line/10" role="progressbar" aria-label="Playback progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 shadow-glow transition-[width] duration-100" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-center text-xs tabular-nums text-muted">{state} · {fmt(done)} / {fmt(total)}</p>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-4">
        <button className="btn-quiet !rounded-full !p-3" onClick={c.restart} disabled={!items.length} aria-label="Restart">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></svg>
        </button>
        <button className="btn-primary !h-14 !w-14 !rounded-full !p-0" onClick={playing ? c.pause : index < 0 ? c.play : c.resume} disabled={!items.length} aria-label={playing ? "Pause" : "Play"}>
          {playing
            ? <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
            : <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z" /></svg>}
        </button>
        <SegmentedControl label="Playback speed" value={speed} onChange={c.setSpeed} options={[{ value: 0.5, label: "0.5x" }, { value: 1, label: "1x" }, { value: 1.5, label: "1.5x" }]} />
      </div>
    </div>
  );
}