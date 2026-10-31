import type { SignItem } from "../types/translation";
import { DEMO_SIGNS } from "./demoSigns";
import { fingerspellClip, hasLetters, spellDuration } from "./alphabet";
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
const failed = new Set<string>();
const demo = new Map(DEMO_SIGNS.map((c) => [c.gloss.toUpperCase(), compileClip(c)]));
const spelled = new Map<string, CompiledClip>();

function validate(raw: unknown): SignClip {
  const c = raw as SignClip;
  if (!c || c.version !== 1 || !Array.isArray(c.keys) || c.keys.length === 0) throw new Error("Invalid sign clip");
  for (const k of c.keys) if (typeof k.t !== "number" || k.t < 0 || k.t > 1) throw new Error("Clip keyframe time must be 0..1");
  return c;
}

export async function prefetchClips(items: SignItem[]): Promise<void> {
  const urls = [...new Set(items.map((i) => i.clip_url).filter((u): u is string => !!u && !remote.has(u) && !failed.has(u)))];
  await Promise.all(urls.map(async (u) => {
    try {
      const r = await fetch(u);
      if (!r.ok) throw new Error(String(r.status));
      remote.set(u, compileClip(validate(await r.json())));
    } catch { failed.add(u); }
  }));
}

export function getClip(item: SignItem): CompiledClip {
  if (item.clip_url) {
    const c = remote.get(item.clip_url);
    if (c) return c;
  }
  const d = demo.get(item.gloss.toUpperCase());
  if (d) return d;
  let s = spelled.get(item.gloss);
  if (!s) { s = compileClip(fingerspellClip(item.gloss)); spelled.set(item.gloss, s); }
  return s;
}

/** True when this item will be fingerspelled (no real or demo clip is known for it). */
export function willFingerspell(item: SignItem): boolean {
  return !(item.clip_url && !failed.has(item.clip_url)) && !demo.has(item.gloss.toUpperCase()) && hasLetters(item.gloss);
}

/**
 * Fingerspelled glosses need longer than the backend's default timing to be readable.
 * Returns the same array when nothing changes so memoised consumers don't re-run.
 */
export function retimeForAvatar(items: SignItem[]): SignItem[] {
  let changed = false;
  const out = items.map((i) => {
    if (!willFingerspell(i)) return i;
    const need = spellDuration(i.gloss);
    if (i.duration >= need) return i;
    changed = true;
    return { ...i, duration: need };
  });
  return changed ? out : items;
}

export const avatarLabel = (c: CompiledClip | null) =>
  !c ? "Demo Sign Renderer · not an actual ISL sign"
  : c.clip.kind === "dataset" ? "Avatar · sign from dataset clip"
  : c.clip.kind === "fingerspell" ? "Placeholder fingerspelling · not the ISL alphabet"
  : "Demo motion · not verified ISL";
