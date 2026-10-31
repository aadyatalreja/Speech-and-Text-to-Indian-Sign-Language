import { HANDSHAPES } from "./handshapes";
import { parseNmm } from "./nmm";
import type { SignClip } from "./types";

export interface CharacterAsset {
  clip: SignClip;
  duration: number;
  source: string;
  licence: string;
  signer: string;
  review_status: "unverified" | "in_review" | "verified";
}

/** Reject corrupt channels instead of turning them into plausible handshapes. */
export function validateCharacterClip(raw: unknown, character: string): SignClip {
  const clip = raw as SignClip;
  if (!clip || clip.version !== 1 || clip.kind !== "dataset" || clip.gloss !== character ||
    !Array.isArray(clip.keys) || !clip.keys.length) throw new Error("Invalid alphabet clip");
  let previous = -1, hands = false;
  const vector = (value: unknown, size: number) => Array.isArray(value) && value.length === size && value.every(
    (v) => typeof v === "number" && Number.isFinite(v));
  for (const key of clip.keys) {
    if (typeof key.t !== "number" || !Number.isFinite(key.t) || key.t < previous || key.t < 0 || key.t > 1) throw new Error("Invalid alphabet time");
    previous = key.t;
    parseNmm({ brow: key.brow, head: key.head, mouth: key.mouth });
    for (const hand of [key.L, key.R]) {
      if (hand == null) continue;
      hands = true;
      if (!vector(hand.p, 3) || (hand.rot != null && !vector(hand.rot, 3)) ||
        (hand.q != null && (!vector(hand.q, 4) || !hand.q.some((v) => v !== 0)))) throw new Error("Invalid alphabet hand");
      if (hand.shape != null && (typeof hand.shape === "string" ? !Object.prototype.hasOwnProperty.call(HANDSHAPES, hand.shape) :
        !vector(hand.shape, 5) || !hand.shape.every((v) => v >= 0 && v <= 1))) throw new Error("Invalid alphabet handshape");
      for (const [value, min, max] of [[hand.spread, -1, 1], [hand.thumbOut, 0, 1]] as const) {
        if (value != null && (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max)) throw new Error("Invalid alphabet hand channel");
      }
    }
  }
  if (!hands) throw new Error("Alphabet clip requires hand data");
  return clip;
}

export class AlphabetAssets {
  readonly characters = new Map<string, CharacterAsset>();
  private pending: Promise<void> | null = null;
  private revision = 0;
  private listeners = new Set<() => void>();
  getRevision = () => this.revision;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };

  load(fetcher: typeof fetch = fetch): Promise<void> {
    if (this.pending) return this.pending;
    this.pending = (async () => {
      try {
        const response = await fetcher("/signs/alphabet/manifest.json");
        if (!response.ok) throw new Error("Alphabet manifest unavailable");
        const manifest = await response.json();
        if (manifest?.version !== 1 || !manifest.characters || typeof manifest.characters !== "object" || Array.isArray(manifest.characters)) throw new Error("Invalid alphabet manifest");
        await Promise.all(Object.entries(manifest.characters).map(async ([character, raw]) => {
          try {
            const entry = raw as Record<string, unknown>;
            if (entry?.review_decision === "rejected") return;
            if (!/^[A-Z0-9]$/.test(character) || entry?.clip == null) return;
            if (typeof entry.clip !== "string" || !/^[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*\.json$/.test(entry.clip)) throw new Error("Invalid alphabet path");
            if (![entry.source, entry.licence, entry.signer].every((v) => typeof v === "string" && v.trim()) ||
              !["unverified", "in_review", "verified"].includes(entry.review_status as string) ||
              typeof entry.duration !== "number" || !Number.isFinite(entry.duration) || entry.duration <= 0 || entry.duration > 30) throw new Error("Missing alphabet provenance/duration");
            const asset = await fetcher(`/signs/alphabet/${entry.clip}`);
            if (!asset.ok) throw new Error("Alphabet clip unavailable");
            const clip = validateCharacterClip(await asset.json(), character);
            this.characters.set(character, { clip, duration: entry.duration, source: entry.source as string,
              licence: entry.licence as string, signer: entry.signer as string,
              review_status: entry.review_status as CharacterAsset["review_status"] });
          } catch { /* Missing or invalid character keeps an honest fallback. */ }
        }));
      } catch { /* Legacy backends without a manifest remain playable as demos. */ }
      this.revision++;
      for (const listener of this.listeners) listener();
    })();
    return this.pending;
  }
}

export const alphabetAssets = new AlphabetAssets();
