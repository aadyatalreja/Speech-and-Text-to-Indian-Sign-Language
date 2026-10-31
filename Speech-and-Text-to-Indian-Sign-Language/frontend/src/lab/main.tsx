import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import AvatarCanvas from "../avatar/AvatarCanvas";
import { DEMO_SIGNS } from "../avatar/demoSigns";
import { fingerspellClip } from "../avatar/alphabet";
import { compileClip } from "../avatar/pose";
import type { SignClip } from "../avatar/types";
import "../styles/index.css";

/**
 * Developer tool (dev server only, /lab.html): author, scrub and loop any sign clip on the avatar.
 *   /lab.html?g=HELLO&t=0.5      pose a bundled demo sign at t=0.5
 *   /lab.html?spell=NAMASTE      fingerspell a word
 * Paste clip JSON (schema in src/avatar/types.ts) into the box to try your own sign.
 */
const params = new URLSearchParams(location.search);
const initial = (): SignClip => {
  const sp = params.get("spell");
  if (sp) return fingerspellClip(sp);
  const g = (params.get("g") ?? "HELLO").toUpperCase();
  return DEMO_SIGNS.find((s) => s.gloss === g) ?? DEMO_SIGNS[0];
};
const ITEM = { gloss: "LAB", sign_id: null, available: true, duration: 1, pause_after: 0, asset_type: "demo", video_url: null };

function Lab() {
  const [json, setJson] = useState(() => JSON.stringify(initial(), null, 1));
  const [t, setT] = useState(Number(params.get("t") ?? 0));
  const [loop, setLoop] = useState(false);
  const [secs, setSecs] = useState(2);
  const raf = useRef(0);

  const parsed = useMemo(() => {
    try { const c = JSON.parse(json) as SignClip; return { c: compileClip(c), err: null as string | null }; }
    catch (e) { return { c: null, err: (e as Error).message }; }
  }, [json]);

  useEffect(() => {
    if (!loop) return;
    const start = performance.now();
    const tick = (n: number) => { setT((((n - start) / 1000) / secs) % 1); raf.current = requestAnimationFrame(tick); };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [loop, secs]);

  return (
    <div className="mx-auto grid max-w-5xl gap-4 p-4 lg:grid-cols-[3fr_2fr]">
      <div>
        <div className="relative aspect-video overflow-hidden rounded-card avatar-stage ring-1 ring-line/10" id="stage">
          {parsed.c && <AvatarCanvas item={ITEM} progress={t} playing={loop} override={parsed.c} />}
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm">
          <input aria-label="time" type="range" min={0} max={1} step={0.005} value={t} onChange={(e) => { setLoop(false); setT(Number(e.target.value)); }} className="flex-1" />
          <span className="tabular-nums">{t.toFixed(2)}</span>
          <button className="btn-primary" onClick={() => setLoop(!loop)}>{loop ? "Stop" : "Loop"}</button>
          <label className="text-muted">sec <input type="number" min={0.5} max={10} step={0.5} value={secs} onChange={(e) => setSecs(Number(e.target.value))} className="w-14 rounded border border-line/20 bg-transparent px-1" /></label>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {DEMO_SIGNS.map((s) => <button key={s.id} className="btn-quiet !px-2 !py-1 text-xs" onClick={() => setJson(JSON.stringify(s, null, 1))}>{s.gloss}</button>)}
        </div>
      </div>
      <div>
        <textarea aria-label="clip json" value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false}
          className="h-[28rem] w-full rounded-card border border-line/20 bg-transparent p-2 font-mono text-xs" />
        {parsed.err && <p className="mt-1 text-xs text-warn">{parsed.err}</p>}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><Lab /></StrictMode>);
