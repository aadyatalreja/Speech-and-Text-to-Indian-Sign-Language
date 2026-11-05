import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import AvatarCanvas from "../avatar/AvatarCanvas";
import { isCharacterId } from "../avatar/characters";

// preview a signer look with ?character=arav|anya|dev|devi
const LAB_CHARACTER = (() => { const c = new URLSearchParams(window.location.search).get("character"); return isCharacterId(c) ? c : "arav"; })();
import { SYNTHETIC_V2 } from "./syntheticV2";
import { DEMO_SIGNS } from "../avatar/demoSigns";
import { fingerspellClip, spellingLabel } from "../avatar/alphabet";
import { alphabetAssets } from "../avatar/alphabetAssets";
import { compileClip } from "../avatar/pose";
import type { SignClip } from "../avatar/types";
import { parseNmm, mergeNmm } from "../avatar/nmm";
import { sampleClip, transitionPose } from "../avatar/pose";
import "../styles/index.css";

/**
 * Developer tool (dev server only, /lab.html): author, scrub and loop any sign clip on the avatar.
 *   /lab.html?g=HELLO&t=0.5      pose a bundled demo sign at t=0.5
 *   /lab.html?spell=NAMASTE      fingerspell a word
 * Paste clip JSON (schema in src/avatar/types.ts) into the box to try your own sign.
 */
const LAB_CLIPS: SignClip[] = [...DEMO_SIGNS, ...SYNTHETIC_V2];
const params = new URLSearchParams(location.search);
const initial = (): SignClip => {
  const sp = params.get("spell");
  if (sp) return fingerspellClip(sp);
  const g = (params.get("g") ?? "HELLO").toUpperCase();
  return LAB_CLIPS.find((s) => s.gloss === g) ?? DEMO_SIGNS[0];
};
const ITEM = { gloss: "LAB", sign_id: null, available: true, duration: 1, pause_after: 0, asset_type: "demo", video_url: null };

function Lab() {
  const [json, setJson] = useState(() => JSON.stringify(initial(), null, 1));
  const [t, setT] = useState(Number(params.get("t") ?? 0));
  const [loop, setLoop] = useState(false);
  const [secs, setSecs] = useState(2);
  const [recorded, setRecorded] = useState<{ gloss: string; clip_url: string }[]>([]);
  const [clipError, setClipError] = useState<string | null>(null);
  const [previousGloss, setPreviousGloss] = useState("");
  const [transitionSeconds, setTransitionSeconds] = useState(0.18);
  const previousClip = useMemo(() => {
    const source = LAB_CLIPS.find((clip) => clip.gloss === previousGloss);
    return source ? compileClip(source) : null;
  }, [previousGloss]);
  const [markerJson, setMarkerJson] = useState("{}");
  const markers = useMemo(() => {
    try { return { nmm: parseNmm(JSON.parse(markerJson)), err: null as string | null }; }
    catch (e) { return { nmm: {}, err: (e as Error).message }; }
  }, [markerJson]);
  const labItem = useMemo(() => ({ ...ITEM, duration: secs, transition_duration: transitionSeconds, nmm: markers.nmm }), [markers, secs, transitionSeconds]);
  const raf = useRef(0);

  const parsed = useMemo(() => {
    try { const c = JSON.parse(json) as SignClip; return { c: compileClip(c), err: null as string | null }; }
    catch (e) { return { c: null, err: (e as Error).message }; }
  }, [json]);
  const preview = useMemo(() => parsed.c && compileClip(mergeNmm(parsed.c.clip, markers.nmm)), [parsed, markers]);
  useEffect(() => {
    let active = true;
    const spelling = params.get("spell");
    if (spelling) void alphabetAssets.load().then(() => {
      if (active) setJson(JSON.stringify(fingerspellClip(spelling), null, 1));
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/avatar-clips", { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error("Could not load the imported clip list.");
        return response.json();
      })
      .then(setRecorded)
      .catch(() => { if (!controller.signal.aborted) setClipError("Could not load the imported clip list."); });
    return () => controller.abort();
  }, []);

  async function previewRecorded(url: string) {
    setClipError(null);
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error("Could not load that imported clip.");
      const clip: SignClip = await response.json();
      compileClip(clip);
      setLoop(false);
      setT(0);
      setSecs(clip.duration ?? 2);
      setJson(JSON.stringify(clip, null, 1));
    } catch {
      setClipError("Could not load that imported clip.");
    }
  }

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
          {parsed.c && <AvatarCanvas item={labItem} progress={t} playing={loop} override={parsed.c} previousOverride={previousClip} character={LAB_CHARACTER} />}
          <p className="absolute bottom-3 left-3 rounded-full bg-surface/80 px-3 py-1 text-xs text-muted">Experimental rig preview · SYNTHETIC fixtures are not ISL</p>
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm">
          <input aria-label="time" type="range" min={0} max={1} step={0.005} value={t} onChange={(e) => { setLoop(false); setT(Number(e.target.value)); }} className="flex-1" />
          <span className="tabular-nums">{t.toFixed(2)}</span>
          <button className="btn-primary" onClick={() => setLoop(!loop)}>{loop ? "Stop" : "Loop"}</button>
          <label className="text-muted">sec <input type="number" min={0.5} max={10} step={0.5} value={secs} onChange={(e) => setSecs(Number(e.target.value))} className="w-14 rounded border border-line/20 bg-transparent px-1" /></label>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {LAB_CLIPS.map((s) => <button key={s.id} className="btn-quiet !px-2 !py-1 text-xs" onClick={() => setJson(JSON.stringify(s, null, 1))}>{s.gloss}</button>)}
        </div>
        {recorded.length > 0 && <label className="mt-3 block text-sm">
          Imported signer clips ({recorded.length}){" "}
          <select className="rounded border border-line/20 bg-surface p-1" value=""
            onChange={event => { if (event.target.value) void previewRecorded(event.target.value); }}>
            <option value="">Choose a sign</option>
            {recorded.map(clip => <option key={clip.gloss} value={clip.clip_url}>{clip.gloss}</option>)}
          </select>
        </label>}
        {clipError && <p role="status" className="mt-2 text-xs text-warn">{clipError}</p>}
        {parsed.c?.clip.kind === "fingerspell" && <p className="mt-2 text-xs text-muted">{spellingLabel(parsed.c.clip)}</p>}
        <label className="mt-4 block text-sm">Previous clip for transition preview <select className="rounded border border-line/20 bg-surface p-1" value={previousGloss} onChange={(e) => setPreviousGloss(e.target.value)}>
          <option value="">None</option>{LAB_CLIPS.map((clip) => <option key={clip.id} value={clip.gloss}>{clip.gloss} · demo</option>)}
        </select></label>
        <label className="mt-2 block text-sm">Transition seconds <input type="number" min={0} max={1} step={0.05} value={transitionSeconds}
          onChange={(e) => { const value = Number(e.target.value); if (Number.isFinite(value)) setTransitionSeconds(Math.min(1, Math.max(0, value))); }} className="w-20 rounded border border-line/20 bg-transparent p-1" /></label>
      </div>
      <div>
        <textarea aria-label="clip json" value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false}
          className="h-[28rem] w-full rounded-card border border-line/20 bg-transparent p-2 font-mono text-xs" />
        {parsed.err && <p className="mt-1 text-xs text-warn">{parsed.err}</p>}
        <label className="mt-4 block text-sm" htmlFor="nmm-json">Item NMM override JSON · rig preview / not verified ISL</label>
        <textarea id="nmm-json" value={markerJson} onChange={(e) => setMarkerJson(e.target.value)} spellCheck={false}
          placeholder={'{"brow":0,"head":[0,0,0],"mouth":0}'}
          className="mt-2 h-24 w-full rounded-card border border-line/20 bg-transparent p-2 font-mono text-xs" />
        {markers.err && <p role="alert" className="text-xs text-warn">{markers.err}</p>}
        <p className="mt-2 text-xs text-muted">Use an item’s nmm object from /api/translate. Empty channels preserve the clip’s facial motion. Values are numeric rig channels; no ISL mapping is implied.</p>
        {preview && <output className="mt-2 block text-xs text-muted">Preview channels at scrub time: {JSON.stringify((({ brow, head, mouth, face, torso, R, L }) => ({ brow, head, mouth, face, torso, right_fingers: R.fingers, left_fingers: L.fingers }))(transitionPose(previousClip ? sampleClip(previousClip, 1) : null, preview, t, transitionSeconds, secs)))}</output>}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><Lab /></StrictMode>);
