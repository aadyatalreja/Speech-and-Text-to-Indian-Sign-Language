import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TimelinePlayback } from "./timelinePlayback";
import type { SignItem } from "../types/translation";
const item = (gloss: string, duration = 1): SignItem => ({ gloss, duration, pause_after: 0.2, sign_id: gloss, available: true, asset_type: "demo", video_url: null });
let player: TimelinePlayback;
beforeEach(() => { vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "performance"] }); player = new TimelinePlayback(); });
afterEach(() => { player.controller.pause(); vi.useRealTimers(); });
it("gives every sign its full duration without carrying completion into the next", () => {
  player.setItems([item("A"), item("B")]); player.controller.play();
  vi.advanceTimersByTime(1200); expect(player.getSnapshot()).toMatchObject({ index: 1, progress: 0 });
  vi.advanceTimersByTime(600); expect(player.getSnapshot().progress).toBeCloseTo(0.5);
  vi.advanceTimersByTime(600); expect(player.getSnapshot()).toMatchObject({ playing: false, progress: 1 });
});
it("preserves base time across pause, speed change, and retiming", () => {
  player.setItems([item("A")]); player.controller.play(); vi.advanceTimersByTime(400);
  player.controller.pause(); vi.advanceTimersByTime(1000); player.setItems([item("A", 2)]);
  player.controller.setSpeed(0.5); player.controller.resume(); vi.advanceTimersByTime(800);
  expect(player.getSnapshot().progress).toBeCloseTo(0.8 / 2.2);
  player.controller.restart(); expect(player.getSnapshot().progress).toBe(0);
});
it("starts when streamed data arrives and resumes after catching up", () => {
  player.controller.play(); player.setItems([item("A")]); vi.advanceTimersByTime(1200);
  player.setItems([item("A"), item("B")]); expect(player.getSnapshot()).toMatchObject({ index: 1, playing: true });
  player.reset(); expect(player.getSnapshot()).toMatchObject({ index: -1, progress: 0, playing: false });
});
