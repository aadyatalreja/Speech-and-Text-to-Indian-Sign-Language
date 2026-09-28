import type { SignAnimationController, SignItem } from "../types/translation";
interface Props { items: SignItem[]; index: number; progress: number; playing: boolean; speed: number; c: SignAnimationController }
export default function SignPlayer({ items, index, progress, playing, speed, c }: Props) {
  const total = items.length;
  const pct = total && index >= 0 ? Math.round(((index + progress) / total) * 100) : 0;
  return (
    <div className="mt-4 rounded-xl border-2 border-ink bg-panel p-4">
      <p aria-live="polite" className="font-bold">Current sign: {index >= 0 && items[index] ? items[index].gloss.replace("_", " ") : "—"}</p>
      <div className="my-3 h-3 w-full overflow-hidden rounded bg-line" role="progressbar" aria-label="Playback progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <div className="h-full bg-ink" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="btn" onClick={c.restart} disabled={!total}>◀ Restart</button>
        {playing
          ? <button className="btn bg-saffron" onClick={c.pause}>⏸ Pause</button>
          : <button className="btn bg-saffron" onClick={index < 0 ? c.play : c.resume} disabled={!total}>▶ Play</button>}
        <label className="ml-auto flex items-center gap-2">Speed
          <select className="rounded-lg border-2 border-ink bg-panel px-2 py-2" value={speed} onChange={(e) => c.setSpeed(Number(e.target.value))}>
            <option value={0.5}>0.5x</option><option value={1}>1x</option><option value={1.5}>1.5x</option>
          </select>
        </label>
      </div>
    </div>
  );
}
