import { describe, expect, it } from "vitest";
import { mergeNmm, parseNmm } from "./nmm";
import { compileClip, idlePose, sampleClip, transitionPose, restPose } from "./pose";
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

it("animates the explicit demo negation rule with numeric yaw and preserves manual tracks", () => {
  const nmm = { head: [0, 12, 0] as [number, number, number], brow: -0.35 };
  const saved = JSON.stringify(clip);
  const shake = compileClip(mergeNmm(clip, nmm, ["negation_nmm_pending_review"]));
  expect(sampleClip(shake, 0.125).head[1]).toBeCloseTo(12);
  expect(sampleClip(shake, 0.375).head[1]).toBeCloseTo(-12);
  expect(sampleClip(shake, 1).head[1]).toBeCloseTo(0);
  for (const t of [0, 0.125, 0.375, 1]) {
    expect(sampleClip(shake, t).R).toEqual(sampleClip(compileClip(clip), t).R);
    expect(sampleClip(shake, t).brow).toBe(-0.35);
  }
  expect(sampleClip(compileClip(mergeNmm(clip, nmm)), 0.375).head[1]).toBe(12);
  expect(JSON.stringify(clip)).toBe(saved);
});

it("eases the first expression in and preserves common sentence channels through a two-sign boundary", () => {
  const first = compileClip(mergeNmm(clip, { brow: 0.55, mouth: 0.3 }));
  const second = compileClip(mergeNmm({ ...clip, id: "second" }, { brow: 0.55, mouth: 0.3 }));
  expect(transitionPose(restPose(), first, 0, 0.2, 1).brow).toBe(0);
  expect(transitionPose(restPose(), first, 0.1, 0.2, 1).brow).toBeCloseTo(0.275);
  // Trailing INTER_SIGN_PAUSE holds the end sample; next onset starts from it.
  const hold = sampleClip(first, 1);
  for (const t of [0, 0.01, 0.1, 0.2, 1]) {
    const next = transitionPose(hold, second, t, 0.2, 1);
    expect(next.brow).toBeCloseTo(0.55);
    expect(next.face!.brow_inner_up).toBeCloseTo(0.55);
    expect(next.mouth).toBeCloseTo(0.3);
  }
});

it("adds periodic idle blink and micro-movement only during holds and respects explicit neutral channels", () => {
  const rest = restPose();
  expect(idlePose(rest, 0.11, false)).toBe(rest);
  const idle = idlePose(rest, 0.11, true);
  expect(idle.face!.eye_blink).toBeCloseTo(1);
  expect(idlePose(rest, 4.71, true).face!.eye_blink).toBeCloseTo(1);
  expect(idlePose(rest, 1, true).face!.eye_blink).toBe(0);
  expect(idle.head).not.toEqual(rest.head);
  const authored = sampleClip(compileClip({ version: 2, id: "neutral", gloss: "SYNTHETIC", kind: "demo", keys: [{ t: 0, head: [0, 0, 0], face: { eye_blink: 0, gaze_x: 0.5 } }] }), 0);
  const gated = idlePose(authored, 0.11, true);
  expect(gated.head).toEqual([0, 0, 0]);
  expect(gated.face!.eye_blink).toBe(0);
  expect(gated.face!.gaze_x).toBe(0.5);
  expect(rest.head).toEqual([0, 0, 0]);
});
