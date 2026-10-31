import type { SignItem } from "../types/translation";
import { DEMO_SIGNS } from "./demoSigns";
import { fingerspellClip, hasLetters, spellDuration, spellingLabel } from "./alphabet";
import { alphabetAssets } from "./alphabetAssets";
import { compileClip, type CompiledClip } from "./pose";
import type { SignClip } from "./types";

/**
 * Resolves a backend SignItem to something the avatar can perform. Order:
 *   1. a clip served by the backend (item.clip_url)  -> kind "dataset" (or whatever the file says)
 *   2. a bundled demo clip for the gloss             -> kind "demo"
 *   3. fingerspelling the gloss                      -> kind "fingerspell"
 * So every gloss can be performed; unknown ones are spelled instead of skipped.
 */

const remote = new Map<string, CompiledClip>();       // by url
const remoteViews = new WeakMap<CompiledClip, Map<string, CompiledClip>>();
const failed = new Set<string>();
const demo = new Map(DEMO_SIGNS.map((c) => [c.gloss.toUpperCase(), compileClip(c)]));
const spelled = new Map<string, CompiledClip>();
let clipRevision = 0;
const clipListeners = new Set<() => void>();
export const getClipRevision = () => clipRevision;
export const subscribeClips = (callback: () => void) => { clipListeners.add(callback); return () => { clipListeners.delete(callback); }; };

function validate(raw: unknown): SignClip {
  const c = raw as SignClip;
  if ((raw as { review_decision?: string })?.review_decision === "rejected") throw new Error("Rejected clip");
  if (!c || c.version !== 1 || !Array.isArray(c.keys) || c.keys.length === 0) throw new Error("Invalid sign clip");
  for (const k of c.keys) if (typeof k.t !== "number" || k.t < 0 || k.t > 1) throw new Error("Clip keyframe time must be 0..1");
  return c;
}

export async function prefetchClips(items: SignItem[]): Promise<void> {
  await alphabetAssets.load();
  const urls = [...new Set(items.map((i) => i.clip_url).filter((u): u is string => !!u && !remote.has(u) && !failed.has(u)))];
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
  const explicitFs = item.gloss.toUpperCase().startsWith("FS:");
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
  }
  const d = !explicitFs && demo.get(item.gloss.toUpperCase());
  if (d) return d;
  const source = fingerspellClip(item.gloss);
  let s = spelled.get(item.gloss);
  if (!s || s.clip !== source) { s = compileClip(source); spelled.set(item.gloss, s); }
  return s;
}

/** True when this item will be fingerspelled (no real or demo clip is known for it). */
export function willFingerspell(item: SignItem): boolean {
  if (item.gloss.toUpperCase().startsWith("FS:")) return true;
  return !(item.clip_url && !failed.has(item.clip_url)) && !demo.has(item.gloss.toUpperCase()) && (hasLetters(item.gloss) || /\d/.test(item.gloss));
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
  : c.clip.kind === "dataset" ? (c.clip.review_status === "verified"
    ? "Avatar · reviewed dataset clip" : "Dataset clip · demo / not verified ISL")
  : c.clip.kind === "fingerspell" ? spellingLabel(c.clip)
  : "Demo motion · not verified ISL";

export const videoLabel = (items: SignItem[]) => items.length > 0 && items.every((item) => item.review_status === "verified")
  ? "Video · reviewed assets" : "Video · demo / not verified ISL";
