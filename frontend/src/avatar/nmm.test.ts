import { describe, expect, it } from "vitest";
import { mergeNmm, parseNmm } from "./nmm";
import { compileClip, sampleClip } from "./pose";
import type { SignClip } from "./types";

// Numeric rig fixtures only; these are not ISL marker definitions.
const clip: SignClip = { version: 1, id: "fixture", gloss: "FIXTURE", kind: "demo", keys: [
  { t: 0, R: { p: [0, 0, 0] }, head: [1, 2, 3], brow: -0.2, mouth: 0.1 },
  { t: 1, R: { p: [1, 1, 1] }, head: [2, 3, 4], brow: 0.2, mouth: 0.3 },
] };

describe("item non-manual marker playback and lab parsing", () => {
  it("overrides configured channels across every key without mutating the cached clip", () => {
    const merged = mergeNmm(clip, { brow: 0, head: [5, 6, 7] });
    for (const t of [0, 0.5, 1]) {
      const pose = sampleClip(compileClip(merged), t);
      expect(pose.brow).toBe(0);
      expect(pose.head).toEqual([5, 6, 7]);
      expect(pose.mouth).toBeCloseTo(sampleClip(compileClip(clip), t).mouth);
      expect(pose.R).toEqual(sampleClip(compileClip(clip), t).R);
    }
    expect(clip.keys[0].brow).toBe(-0.2);
    expect(clip.keys[0].head).toEqual([1, 2, 3]);
  });
  it("preserves original clip identity and tracks when no markers are configured", () => {
    expect(mergeNmm(clip)).toBe(clip);
    expect(mergeNmm(clip, { brow: null, head: null, mouth: null })).toBe(clip);
  });
  it("holds sentence channels across successive signs", () => {
    for (const sign of [clip, { ...clip, id: "second" }]) {
      expect(sampleClip(compileClip(mergeNmm(sign, { mouth: 0.4 })), 0).mouth).toBe(0.4);
      expect(sampleClip(compileClip(mergeNmm(sign, { mouth: 0.4 })), 1).mouth).toBe(0.4);
    }
  });
  it.each([[], null, { brow: 2 }, { mouth: -1 }, { head: [1, 2] },
    { head: [0, 100, 0] }, { brow: NaN }, { mouth: Infinity }, { unknown: 1 }])("rejects invalid lab channels %j", (raw) => {
    expect(() => parseNmm(raw)).toThrow();
  });
});
