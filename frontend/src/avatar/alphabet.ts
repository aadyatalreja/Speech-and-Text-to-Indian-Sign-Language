import { FACE_KEYS, TORSO_KEYS } from "./pose";
import type { KeyframeV2, SignClip } from "./types";
import { CHARACTER_POSES } from "./characterPoses";
import { alphabetAssets, type CharacterAsset } from "./alphabetAssets";

export function hasLetters(gloss: string): boolean {
  return /[A-Z0-9]/i.test(gloss.replace(/^FS:/i, ""));
}

export function spellDuration(gloss: string): number {
  return fingerspellClip(gloss).spelling!.duration;
}

function referencePose(symbol: string): SignClip | null {
  const pose = CHARACTER_POSES[symbol];
  if (!pose) return null;
  return { version: 1, id: `reference:${symbol}`, gloss: symbol, kind: "demo",
    keys: [{ t: 0, R: null, L: null }, { t: 0.25, R: null, L: null, ...pose }, { t: 1, R: null, L: null, ...pose }],
    notes: "Hand-authored avatar pose based on the supplied character charts. Pending signer review." };
}

/** Compose supplied character clips without mirroring or replacing either hand.
 * Source clips retain their original versions. Gaps and repeat separation are engine playback only,
 * and do not claim a signer-reviewed word-level transition.
 */
export function buildSpelling(gloss: string, assets: ReadonlyMap<string, CharacterAsset>): SignClip {
  const symbols = Array.from(gloss.toUpperCase().replace(/^FS:/, ""));
  const missing = new Set<string>(), unverified = new Set<string>(), textOnly = new Set<string>();
  const approximated = new Set<string>();
  const used: NonNullable<SignClip["spelling"]>["assets"] = [];
  const segments = symbols.map((symbol) => {
    if (/^[ _\s-]$/.test(symbol)) return { symbol, duration: 0.25, clip: null };
    const asset = assets.get(symbol);
    if (asset) {
      if (asset.review_status !== "verified") unverified.add(symbol);
      if (!used.some((entry) => entry.character === symbol)) used.push({ character: symbol, source: asset.source,
        licence: asset.licence, signer: asset.signer, review_status: asset.review_status });
      return { symbol, duration: asset.duration, clip: asset.clip };
    }
    missing.add(symbol);
    const clip = referencePose(symbol);
    if (clip) approximated.add(symbol); else textOnly.add(symbol);
    return { symbol, duration: 0.65, clip };
  });
  const gap = 0.12;
  const duration = Math.max(0.6, segments.reduce((sum, segment) => sum + segment.duration, 0) +
    gap * Math.max(0, segments.length - 1) + 0.3);
  const keys: KeyframeV2[] = [];
  const v2 = segments.some(s => s.clip?.version === 2);
  let elapsed = 0;
  segments.forEach((segment, index) => {
    const source: KeyframeV2[] = segment.clip?.keys ?? [{ t: 0, R: null, L: null }];
    // Reset channels omitted by this character so the preceding character's
    // other hand or facial channels cannot leak into its motion.
    keys.push({ R: null, L: null, head: [0, 0, 0], brow: 0, mouth: 0, ...source[0], ...(v2 ? { face: { ...Object.fromEntries(FACE_KEYS.map(k => [k,0])), ...source[0].face }, torso: { ...Object.fromEntries(TORSO_KEYS.map(k => [k,0])), ...source[0].torso } } : {}), t: elapsed / duration });
    for (const key of source) keys.push({ ...key, t: (elapsed + key.t * segment.duration) / duration });
    keys.push({ ...source[source.length - 1], t: (elapsed + segment.duration) / duration });
    elapsed += segment.duration;
    if (index < segments.length - 1) {
      if (segment.symbol === segments[index + 1].symbol) keys.push({ t: (elapsed + gap / 2) / duration, R: null, L: null });
      elapsed += gap;
    }
  });
  if (!keys.length) keys.push({ t: 0, R: null, L: null });
  keys.push({ ...keys[keys.length - 1], t: 1 });
  return { version: v2 ? 2 : 1, id: `spell:${gloss.toLowerCase()}`, gloss, kind: "fingerspell", keys,
    notes: "Assembled character playback. Source assets retain per-character provenance; transitions are engine-generated.",
    spelling: { duration, missing: [...missing], unverified: [...unverified], textOnly: [...textOnly], assets: used, approximated: [...approximated] } } as SignClip;
}

const cache = new Map<string, SignClip>();
let cachedRevision = -1;
export function fingerspellClip(gloss: string): SignClip {
  if (cachedRevision !== alphabetAssets.getRevision()) {
    cache.clear(); cachedRevision = alphabetAssets.getRevision();
  }
  let clip = cache.get(gloss);
  if (!clip) { clip = buildSpelling(gloss, alphabetAssets.characters); cache.set(gloss, clip); }
  return clip;
}

export function spellingLabel(clip: SignClip): string {
  const spelling = clip.spelling;
  if (!spelling) return "Placeholder fingerspelling · not the ISL alphabet";
  if (spelling.approximated?.length || spelling.textOnly.length) {
    return [
      spelling.unverified.length ? "Unreviewed alphabet clips" : spelling.assets.length ? "Reviewed alphabet clips" : "",
      spelling.approximated?.length ? "Chart-based avatar poses (unreviewed): " + spelling.approximated.join(", ") : "",
      spelling.textOnly.length ? "Text only: " + spelling.textOnly.join(", ") : "",
    ].filter(Boolean).join(" / ");
  }
  if (spelling.unverified.length) return "Alphabet clips · not verified ISL: " + spelling.unverified.join(", ");
  if (!spelling.assets.length) return "No alphabet characters available · text only";
  return "Reviewed alphabet clips · assembled playback";
}
