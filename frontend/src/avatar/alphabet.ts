import type { Curls, Keyframe, SignClip, Vec3 } from "./types";

/**
 * PLACEHOLDER fingerspelling. These are single-hand, ASL-style approximations chosen so that every
 * letter looks different on the avatar. They are NOT the Indian Sign Language manual alphabet (ISL
 * uses two hands for many letters). Replace `LETTERS` with a verified ISL alphabet before use.
 */
interface Letter { c: Curls; spread?: number; thumbOut?: number; rot?: Vec3; path?: Vec3[] }

const L = (c: Curls, extra: Partial<Letter> = {}): Letter => ({ c, ...extra });

export const LETTERS: Record<string, Letter> = {
  A: L([0.1, 1, 1, 1, 1], { thumbOut: 0.1 }),
  B: L([0.9, 0, 0, 0, 0]),
  C: L([0.35, 0.45, 0.45, 0.45, 0.45], { thumbOut: 0.6, rot: [0, -60, 0] }),
  D: L([0.6, 0, 1, 1, 1]),
  E: L([0.8, 0.85, 0.85, 0.85, 0.85]),
  F: L([0.55, 0.55, 0, 0, 0], { spread: 0.5 }),
  G: L([0, 0, 1, 1, 1], { rot: [0, -90, 90] }),
  H: L([0.8, 0, 0, 1, 1], { rot: [0, -90, 90] }),
  I: L([0.8, 1, 1, 1, 0]),
  J: L([0.8, 1, 1, 1, 0], { path: [[0, 0, 0], [0, -0.12, 0], [0.1, -0.15, 0]] }),
  K: L([0.1, 0, 0, 1, 1], { spread: 0.7, thumbOut: 0.5 }),
  L: L([0, 0, 1, 1, 1], { thumbOut: 1 }),
  M: L([0.9, 0.75, 0.75, 0.75, 1]),
  N: L([0.9, 0.75, 0.75, 1, 1]),
  O: L([0.6, 0.6, 0.6, 0.6, 0.6]),
  P: L([0.1, 0, 0, 1, 1], { spread: 0.7, thumbOut: 0.5, rot: [90, 0, 0] }),
  Q: L([0, 0, 1, 1, 1], { thumbOut: 0.8, rot: [0, 0, 180] }),
  R: L([0.8, 0, 0, 1, 1], { spread: -0.6 }),
  S: L([0.7, 1, 1, 1, 1], { thumbOut: 0 }),
  T: L([0.6, 0.9, 1, 1, 1], { thumbOut: 0 }),
  U: L([0.8, 0, 0, 1, 1]),
  V: L([0.8, 0, 0, 1, 1], { spread: 0.9 }),
  W: L([0.8, 0, 0, 0, 1], { spread: 0.8 }),
  X: L([0.8, 0.6, 1, 1, 1]),
  Y: L([0, 1, 1, 1, 0], { thumbOut: 1 }),
  Z: L([0.8, 0, 1, 1, 1], { path: [[0, 0, 0], [0.12, 0, 0], [-0.12, -0.12, 0], [0.12, -0.12, 0]] }),
};

/** Canonical spelling position: right hand, beside the chin, palm to the viewer. */
const HOME: Vec3 = [-0.32, -0.2, 0.55];

export function spellableLetters(gloss: string): string[] {
  return gloss.toUpperCase().replace(/[^A-Z_ -]/g, "").split("").filter((ch) => ch === "_" || ch === " " || ch === "-" || LETTERS[ch]);
}

export function hasLetters(gloss: string): boolean {
  return spellableLetters(gloss).some((ch) => LETTERS[ch]);
}

/** Seconds a spelled gloss needs at speed 1 so each letter is readable. */
export function spellDuration(gloss: string): number {
  const ch = spellableLetters(gloss);
  const letters = ch.filter((c) => LETTERS[c]).length;
  const gaps = ch.length - letters;
  return Math.max(0.6, 0.38 * letters + 0.25 * gaps + 0.3);
}

export function fingerspellClip(gloss: string): SignClip {
  const seq = spellableLetters(gloss);
  const weights = seq.map((c) => (LETTERS[c] ? 1 : 0.5));
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  const keys: Keyframe[] = [];
  let t = 0, prev = "";
  seq.forEach((ch, i) => {
    const w = weights[i] / total;
    const spec = LETTERS[ch];
    if (spec) {
      const mk = (tt: number, off: Vec3 = [0, 0, 0]): Keyframe => ({
        t: Math.min(1, tt),
        R: { p: [HOME[0] + off[0], HOME[1] + off[1], HOME[2] + off[2]], rot: spec.rot ?? [0, 0, 0], shape: spec.c, spread: spec.spread ?? 0, thumbOut: spec.thumbOut ?? 0.25 },
      });
      if (prev === ch) keys.push({ t: t + w * 0.04, R: { p: [HOME[0], HOME[1] - 0.05, HOME[2]], rot: spec.rot ?? [0, 0, 0], shape: spec.c, spread: spec.spread ?? 0, thumbOut: spec.thumbOut ?? 0.25 } });
      if (spec.path) {
        const n = spec.path.length;
        spec.path.forEach((off, k) => keys.push(mk(t + w * (0.3 + (0.6 * k) / (n - 1)), off)));
      } else {
        keys.push(mk(t + w * 0.3), mk(t + w * 0.85));
      }
      prev = ch;
    } else {
      prev = "";
    }
    t += w;
  });
  if (!keys.length) keys.push({ t: 0, R: null }, { t: 1, R: null });
  else { keys[0] = { ...keys[0], t: Math.min(keys[0].t, 0.1) }; keys.push({ ...keys[keys.length - 1], t: 1 }); }
  return {
    version: 1, id: `spell:${gloss.toLowerCase()}`, gloss, kind: "fingerspell", keys,
    notes: "Placeholder fingerspelling. Not the ISL manual alphabet.",
  };
}
