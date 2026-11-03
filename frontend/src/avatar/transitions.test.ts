import { expect, it } from "vitest";
import { compileClip, restPose, sampleClip, transitionPose } from "./pose";
import { retimeForAvatar } from "./library";
import { spellDuration } from "./alphabet";
import type { SignClip } from "./types";

it("starts exactly at previous end and reaches the next motion without a rest snap", () => {
  const previous = restPose(); previous.R.p = [-0.2, 0.4, 0.5]; previous.brow = 0.7;
  const clip: SignClip = { version: 1, id: "fixture", gloss: "FIXTURE", kind: "demo", keys: [
    { t: 0, R: { p: [0.5, 0, 0] }, brow: -0.2 }, { t: 1, R: { p: [0.8, 0, 0] }, brow: 0.2 }] };
  const compiled = compileClip(clip);
  expect(transitionPose(previous, compiled, 0, 0.2, 2).R.p).toEqual(previous.R.p);
  expect(transitionPose(previous, compiled, 0.05, 0.2, 2).R.p[0]).toBeGreaterThan(previous.R.p[0]);
  expect(transitionPose(previous, compiled, 0.1, 0.2, 2)).toEqual(sampleClip(compiled, 0.1));
  expect(transitionPose(previous, compiled, 0, 0, 2)).toEqual(sampleClip(compiled, 0));
});
it("retimes spelling to its actual composition duration even when the old estimate was longer", () => {
  const item = { gloss: "FS:A", duration: 20, pause_after: 0, available: false, sign_id: null, video_url: null, asset_type: "none" };
  expect(retimeForAvatar([item])[0].duration).toBe(spellDuration("FS:A"));
});

it("uses a bounded curved path and eases velocity at inter-sign endpoints", () => {
  const previous = restPose(); previous.R.p = [-0.5, 0, 0.4];
  const clip = compileClip({ version: 1, id: "second", gloss: "SYNTHETIC", kind: "demo", keys: [{ t: 0, R: { p: [0.5, 0, 0.4] } }] });
  const middle = transitionPose(previous, clip, 0.1, 0.2, 1);
  expect(middle.R.p[0]).toBeCloseTo(0);
  expect(middle.R.p[2]).toBeCloseTo(0.46);
  const early = transitionPose(previous, clip, 0.001, 0.2, 1);
  expect(early.R.p[0] - previous.R.p[0]).toBeLessThan(0.00001);
  expect(transitionPose(previous, clip, 0.2, 0.2, 1)).toEqual(sampleClip(clip, 0.2));
});
