import type { SignItem } from "../types/translation";
import { DEMO_SIGNS } from "./demoSigns";
import { fingerspellClip, hasLetters, spellDuration, spellingLabel } from "./alphabet";
import { alphabetAssets } from "./alphabetAssets";
import { compileClip, type CompiledClip } from "./pose";
import type { SignClip } from "./types";

const unavailable = compileClip({
  version: 1, id: "unavailable", gloss: "UNAVAILABLE", kind: "demo",
  notes: "No sign animation available",
  keys: [{ t: 0, L: null, R: null }],
});

const inline = new WeakMap<SignClip, CompiledClip>();
const remote = new Map<string, CompiledClip>();       // by url
const remoteViews = new WeakMap<CompiledClip, Map<string, CompiledClip>>();
const failed = new Set<string>();
const demo = new Map(DEMO_SIGNS.map((c) => [c.gloss.toUpperCase(), compileClip(c)]));
// These two gestures use the hand-authored versions selected for this avatar.
const preferredDemo = new Set(["ME", "YOU"]);
const spelled = new Map<string, CompiledClip>();
let clipRevision = 0;
const clipListeners = new Set<() => void>();
export const getClipRevision = () => clipRevision;
export const subscribeClips = (callback: () => void) => { clipListeners.add(callback); return () => { clipListeners.delete(callback); }; };

function validate(raw: unknown): SignClip {
  const c = raw as SignClip;
  if ((raw as { review_decision?: string })?.review_decision === "rejected") throw new Error("Rejected clip");
  if (!c || (c.version !== 1 && c.version !== 2) || !Array.isArray(c.keys) || c.keys.length === 0) throw new Error("Invalid sign clip");
  for (const k of c.keys) if (typeof k.t !== "number" || k.t < 0 || k.t > 1) throw new Error("Clip keyframe time must be 0..1");
  return c;
}

export async function prefetchClips(items: SignItem[]): Promise<void> {
  await alphabetAssets.load();
  const urls = [...new Set(items.filter((item) => !preferredDemo.has(item.gloss.toUpperCase())).map((item) => item.clip_url).filter((u): u is string => !!u && !remote.has(u) && !failed.has(u)))];
  await Promise.all(urls.map(async (u) => {
    try {
      const r = await fetch(u);
      if (!r.ok) throw new Error(String(r.status));
      const raw = validate(await r.json());
      remote.set(u, compileClip(raw));
    } catch { failed.add(u); }
  }));
  if (urls.length) { clipRevision++; clipListeners.forEach((callback) => callback()); }
}

export function getClip(item: SignItem): CompiledClip {
  if (item.inline_clip) {
    let compiled = inline.get(item.inline_clip);
    if (!compiled) {
      try {
        compiled = compileClip(validate(item.inline_clip));
      } catch {
        compiled = unavailable;
      }
      inline.set(item.inline_clip, compiled);
    }
    return compiled;
  }
  const gloss = item.gloss.toUpperCase();
  const explicitFs = gloss.startsWith("FS:");
  const demoClip = demo.get(gloss);
  if (demoClip && preferredDemo.has(gloss)) return demoClip;
  if (!explicitFs && item.clip_url) {
    const c = remote.get(item.clip_url);
    if (c) {
      const metadata = { source: item.source ?? c.clip.source, licence: item.licence ?? c.clip.licence,
        signer: item.signer ?? c.clip.signer, review_status: item.review_status ?? "unverified" as const };
      const key = JSON.stringify(metadata);
      let views = remoteViews.get(c);
      if (!views) { views = new Map(); remoteViews.set(c, views); }
      let view = views.get(key);
      if (!view) { view = compileClip({ ...c.clip, ...metadata }); views.set(key, view); }
      return view;
    }
    if (item.asset_type === "dataset" && !failed.has(item.clip_url)) return unavailable;
  }
  if (!explicitFs && demoClip) return demoClip;
  if (!willFingerspell(item)) return unavailable;
  const source = fingerspellClip(item.gloss);
  let s = spelled.get(item.gloss);
  if (!s || s.clip !== source) { s = compileClip(source); spelled.set(item.gloss, s); }
  return s;
}

/** A missing sign can be spelled when its gloss contains letters or digits. */
export function willFingerspell(item: SignItem): boolean {
  const gloss = item.gloss.toUpperCase();
  if (item.inline_clip || demo.has(gloss)) return false;
  if (!gloss.startsWith("FS:") && item.clip_url && !failed.has(item.clip_url)) return false;
  return hasLetters(gloss);
}

/**
 * Fingerspelled glosses need longer than the backend's default timing to be readable.
 * Returns the same array when nothing changes so memoised consumers don't re-run.
 */
export function retimeForAvatar(items: SignItem[]): SignItem[] {
  let changed = false;
  const out = items.map((i) => {
    const clip = getClip(i);
    const duration = clip.clip.duration ?? i.clip_duration;
    const need = clip.clip.kind === "fingerspell" ? spellDuration(i.gloss) : duration;
    if (need == null || !Number.isFinite(need) || need <= 0 || i.duration === need) return i;
    changed = true;
    return { ...i, duration: need };
  });
  return changed ? out : items;
}

export const avatarLabel = (c: CompiledClip | null) =>
  !c ? "Demo Sign Renderer · not an actual ISL sign"
  : c.clip.id === unavailable.clip.id ? "No sign animation available"
  : c.clip.kind === "dataset" ? (c.clip.review_status === "verified"
    ? "Avatar · reviewed dataset clip" : "Dataset clip · demo / not verified ISL")
  : c.clip.kind === "fingerspell" ? spellingLabel(c.clip)
  : "Demo motion · not verified ISL";

export const videoLabel = (items: SignItem[]) => items.length > 0 && items.every((item) => item.review_status === "verified")
  ? "Video · reviewed assets" : "Video · demo / not verified ISL";
