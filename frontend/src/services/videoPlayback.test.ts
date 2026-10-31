import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { VideoPlayback, allVideos, anyVideos, missingVideos } from "./videoPlayback";
import type { SignItem } from "../types/translation";

const item = (gloss: string, video_url: string | null = `/${gloss}.mp4`, pause_after = 0.2): SignItem => ({
  gloss, video_url, pause_after, sign_id: gloss, available: true, asset_type: "dataset", duration: 0.6,
});
class FakeMedia extends EventTarget {
  src = ""; currentTime = 0; duration = 4; playbackRate = 1; ended = false;
  play = vi.fn(async () => undefined); pause = vi.fn();
  load = vi.fn(() => { this.currentTime = 0; this.ended = false; });
  end() { this.currentTime = this.duration; this.ended = true; this.dispatchEvent(new Event("ended")); }
}
let playback: VideoPlayback, media: FakeMedia;
beforeEach(() => { vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "performance"] }); playback = new VideoPlayback(); media = new FakeMedia(); playback.attach(media as unknown as HTMLVideoElement); });
afterEach(() => { playback.controller.pause(); playback.attach(null); vi.useRealTimers(); });

it("defaults eligibility to complete nonempty video sequences", () => {
  expect(allVideos([])).toBe(false);
  expect(allVideos([item("A"), item("B")])).toBe(true);
  expect(allVideos([item("A"), item("B", null)])).toBe(false);
  expect(anyVideos([item("A"), item("B", null)])).toBe(true);
  expect(missingVideos([item("A"), item("B", null)])).toEqual(["B"]);
});
it("waits for media ended, then the entire gap, instead of estimated sign duration", () => {
  playback.setItems([item("A"), item("B", "/B.mp4", 0)]);
  playback.controller.play();
  expect(media.src).toBe("/A.mp4");
  vi.advanceTimersByTime(10000);
  expect(playback.getSnapshot().index).toBe(0);
  media.end();
  expect(playback.getSnapshot().phase).toBe("gap");
  vi.advanceTimersByTime(175);
  expect(playback.getSnapshot().index).toBe(0);
  vi.advanceTimersByTime(25);
  expect(playback.getSnapshot().index).toBe(1);
  expect(media.src).toBe("/B.mp4");
  media.end();
  expect(playback.getSnapshot()).toMatchObject({ phase: "finished", playing: false, progress: 1 });
});
it("pauses and resumes gaps without counting paused wall time", () => {
  playback.setItems([item("A", "/A.mp4", 1), item("B")]);
  playback.controller.play(); media.end();
  vi.advanceTimersByTime(400); playback.controller.pause();
  vi.advanceTimersByTime(5000); playback.controller.resume();
  vi.advanceTimersByTime(575);
  expect(playback.getSnapshot().index).toBe(0);
  vi.advanceTimersByTime(25);
  expect(playback.getSnapshot().index).toBe(1);
});
it("applies speed to media and remaining gap time", () => {
  playback.setItems([item("A", "/A.mp4", 1), item("B")]);
  playback.controller.play(); media.end();
  vi.advanceTimersByTime(250); playback.controller.setSpeed(1.5);
  expect(media.playbackRate).toBe(1.5);
  vi.advanceTimersByTime(500);
  expect(playback.getSnapshot().index).toBe(1);
});
it("uses media metadata for progress and keeps currentTime on pause/resume", () => {
  playback.setItems([item("A")]); playback.controller.play();
  media.dispatchEvent(new Event("loadedmetadata"));
  media.currentTime = 2; media.dispatchEvent(new Event("timeupdate"));
  expect(playback.displayItems()[0].duration).toBe(4);
  expect(playback.getSnapshot().progress).toBeCloseTo(2 / 4.2);
  playback.controller.pause(); playback.controller.resume();
  expect(media.currentTime).toBe(2);
});
it("replays consecutive copies of the same video from the beginning", () => {
  playback.setItems([item("A", "/same.mp4", 0), item("A", "/same.mp4", 0)]);
  playback.controller.play(); media.end();
  expect(playback.getSnapshot().index).toBe(1);
  expect(media.currentTime).toBe(0);
  expect(media.load).toHaveBeenCalledTimes(2);
});
it("shows timed text cards for missing clips and restarts finished sequences", () => {
  playback.setItems([item("MISSING", null, 0), item("B", "/B.mp4", 0)]);
  playback.controller.play();
  expect(playback.getSnapshot().phase).toBe("missing");
  vi.advanceTimersByTime(600);
  expect(media.src).toBe("/B.mp4");
  media.end(); playback.controller.resume();
  expect(playback.getSnapshot()).toMatchObject({ index: 0, phase: "missing", playing: true });
});
it("resets on replaced sequences and continues appended streamed items", () => {
  playback.setItems([item("A", "/A.mp4", 0)]); playback.controller.play(); media.end();
  playback.setItems([item("A", "/A.mp4", 0), item("B")]);
  expect(playback.getSnapshot()).toMatchObject({ index: 1, playing: true });
  playback.setItems([item("C")]);
  expect(playback.getSnapshot()).toMatchObject({ index: -1, playing: false });
});
it("surfaces playback failures and detaches events on unmount", async () => {
  playback.setItems([item("A")]); media.play.mockRejectedValueOnce(new Error("blocked"));
  playback.controller.play(); await Promise.resolve(); await Promise.resolve();
  expect(playback.getSnapshot().playing).toBe(false);
  expect(playback.getSnapshot().error).toContain("could not play");
  playback.attach(null); const state = playback.getSnapshot(); media.end();
  expect(playback.getSnapshot()).toBe(state);
});
