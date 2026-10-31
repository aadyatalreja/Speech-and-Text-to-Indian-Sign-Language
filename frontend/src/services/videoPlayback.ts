import type { SignAnimationController, SignItem } from "../types/translation";

export const allVideos = (items: SignItem[]) => items.length > 0 && items.every((item) => !!item.video_url);
export const anyVideos = (items: SignItem[]) => items.some((item) => !!item.video_url);
export const missingVideos = (items: SignItem[]) => items.filter((item) => !item.video_url).map((item) => item.gloss);
export type VideoPhase = "idle" | "video" | "gap" | "missing" | "finished";
export interface VideoState { index: number; playing: boolean; speed: number; progress: number; phase: VideoPhase; error: string | null }

/** Media-ended driven sequence. Only gaps/missing-video cards use a clock. */
export class VideoPlayback {
  private items: SignItem[] = [];
  private media: HTMLVideoElement | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private elapsed = 0;
  private last = 0;
  private epoch = 0;
  private listeners = new Set<() => void>();
  private durations = new Map<number, number>();
  private state: VideoState = { index: -1, playing: false, speed: 1, progress: 0, phase: "idle", error: null };
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private update(values: Partial<VideoState>) { this.state = { ...this.state, ...values }; this.listeners.forEach((listener) => listener()); }
  private stopTimer() { if (this.timer !== null) clearInterval(this.timer); this.timer = null; }
  private item() { return this.items[this.state.index]; }
  private gap() { return Math.max(0, this.item()?.pause_after ?? 0); }
  private duration() { return this.durations.get(this.state.index) ?? this.item()?.duration ?? 0.6; }
  private progress() {
    const duration = this.duration(), gap = this.gap();
    const time = this.state.phase === "gap" ? duration + this.elapsed : this.state.phase === "missing" ? this.elapsed : this.media?.currentTime ?? 0;
    return Math.min(1, Math.max(0, time / Math.max(0.001, duration + gap)));
  }
  displayItems() { return this.items.map((item, index) => this.durations.has(index) ? { ...item, duration: this.durations.get(index)! } : item); }
  setItems(items: SignItem[]) {
    if (this.items === items) return;
    const prefix = this.items.every((item, index) => items[index]?.gloss === item.gloss && items[index]?.video_url === item.video_url);
    this.items = items;
    if (!prefix) { this.reset(); this.durations.clear(); }
    if (this.state.phase === "finished" && this.state.index + 1 < items.length) this.begin(this.state.index + 1);
    this.update({});
  }
  attach = (media: HTMLVideoElement | null) => {
    if (this.media === media) return;
    if (this.media) { this.media.pause(); for (const [name, callback] of this.events) this.media.removeEventListener(name, callback); }
    this.media = media;
    if (media) { for (const [name, callback] of this.events) media.addEventListener(name, callback); this.load(); }
  };
  private load() {
    const url = this.item()?.video_url;
    if (!this.media) return;
    this.media.playbackRate = this.state.speed;
    if (url && this.state.phase === "video") {
      this.media.src = url; this.media.load();
      if (this.state.playing) this.startMedia();
    }
  }
  private startMedia() {
    if (!this.media) return;
    const epoch = this.epoch;
    void this.media.play().catch(() => {
      if (epoch === this.epoch && this.state.playing && this.state.phase === "video") this.update({ playing: false, error: "Video could not play. Press Play to retry or choose Avatar." });
    });
  }
  private begin(index: number) {
    this.stopTimer(); this.media?.pause(); this.epoch++; this.elapsed = 0;
    const item = this.items[index];
    if (!item) { this.update({ playing: false, phase: "idle", index: -1, progress: 0 }); return; }
    this.update({ index, playing: true, progress: 0, error: null, phase: item.video_url ? "video" : "missing" });
    if (item.video_url) this.load(); else this.startClock();
  }
  private advance() {
    this.stopTimer();
    if (this.state.index + 1 < this.items.length) this.begin(this.state.index + 1);
    else this.update({ playing: false, phase: "finished", progress: 1 });
  }
  private startClock() { this.stopTimer(); this.last = performance.now(); this.timer = setInterval(this.tick, 25); }
  private tick = () => {
    if (!this.state.playing) return;
    const now = performance.now(); this.elapsed += (now - this.last) * this.state.speed / 1000; this.last = now;
    const limit = this.state.phase === "gap" ? this.gap() : this.duration() + this.gap();
    if (this.elapsed + 1e-9 >= limit) this.advance(); else this.update({ progress: this.progress() });
  };
  private metadata = () => {
    if (this.state.phase !== "video") return;
    const duration = this.media?.duration;
    if (duration && Number.isFinite(duration) && duration > 0 && this.state.index >= 0) {
      this.durations.set(this.state.index, duration); this.update({ progress: this.progress() });
    }
  };
  private timeupdate = () => { if (this.state.phase === "video") this.update({ progress: this.progress() }); };
  private ended = () => {
    if (this.state.phase !== "video" || !this.state.playing || !this.media?.ended) return;
    this.metadata(); this.elapsed = 0;
    if (!this.gap()) this.advance(); else { this.update({ phase: "gap", progress: this.progress() }); this.startClock(); }
  };
  private error = () => {
    if (this.state.phase !== "video") return;
    this.stopTimer(); this.media?.pause(); this.update({ playing: false, error: "Signer video is unavailable. Choose Avatar or retry playback." });
  };
  private events: [string, EventListener][] = [["loadedmetadata", this.metadata], ["durationchange", this.metadata], ["timeupdate", this.timeupdate], ["ended", this.ended], ["error", this.error]];
  reset = () => { this.stopTimer(); this.epoch++; this.media?.pause(); this.elapsed = 0; this.update({ index: -1, playing: false, progress: 0, phase: "idle", error: null }); };
  readonly controller: SignAnimationController = {
    play: () => this.begin(0), restart: () => this.begin(0),
    pause: () => {
      if (this.state.playing && ["gap", "missing"].includes(this.state.phase)) this.tick();
      this.stopTimer(); this.media?.pause(); this.epoch++; this.update({ playing: false });
    },
    resume: () => {
      if (this.state.index < 0 || this.state.phase === "finished") { this.begin(0); return; }
      this.update({ playing: true, error: null });
      if (this.state.phase === "video") { if (this.media?.ended) this.ended(); else this.startMedia(); } else this.startClock();
    },
    setSpeed: (speed) => {
      if (![0.5, 1, 1.5].includes(speed)) return;
      if (this.state.playing && ["gap", "missing"].includes(this.state.phase)) this.tick();
      this.update({ speed }); if (this.media) this.media.playbackRate = speed;
    },
  };
}
