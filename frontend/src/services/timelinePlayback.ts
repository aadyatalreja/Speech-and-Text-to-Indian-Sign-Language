import type { SignAnimationController, SignItem } from "../types/translation";

/** Avatar timer using base seconds, preserving time across pauses and retiming. */
export class TimelinePlayback {
  private items: SignItem[] = [];
  private elapsed = 0;
  private last = 0;
  private timer: ReturnType<typeof setInterval> | null = null;
  private waiting = false;
  private queued = false;
  private listeners = new Set<() => void>();
  private state = { index: -1, playing: false, speed: 1, progress: 0 };
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private update(values: Partial<typeof this.state>) { this.state = { ...this.state, ...values }; this.listeners.forEach((listener) => listener()); }
  private stop() { if (this.timer !== null) clearInterval(this.timer); this.timer = null; }
  private clock() { this.stop(); this.last = performance.now(); this.timer = setInterval(this.tick, 25); }
  private begin(index: number) {
    this.stop(); this.elapsed = 0; this.waiting = false;
    if (!this.items[index]) { this.reset(); return; }
    this.update({ index, playing: true, progress: 0 }); this.clock();
  }
  private tick = () => {
    if (!this.state.playing) return;
    const now = performance.now(); this.elapsed += (now - this.last) * this.state.speed / 1000; this.last = now;
    const item = this.items[this.state.index];
    if (!item) { this.reset(); return; }
    const total = Math.max(0.001, item.duration + item.pause_after);
    if (this.elapsed + 1e-9 >= total) {
      if (this.state.index + 1 < this.items.length) this.begin(this.state.index + 1);
      else { this.stop(); this.waiting = true; this.update({ playing: false, progress: 1 }); }
    } else this.update({ progress: Math.max(0, this.elapsed / total) });
  };
  setItems(items: SignItem[]) {
    if (this.items === items) return;
    const samePrefix = this.items.every((item, index) => items[index]?.gloss === item.gloss);
    this.items = items;
    if (this.queued && items.length) { this.queued = false; this.begin(0); }
    else if (!samePrefix) this.reset();
    else if (this.waiting && this.state.index + 1 < items.length) this.begin(this.state.index + 1);
    else if (this.state.playing) this.tick();
  }
  reset = () => { this.stop(); this.elapsed = 0; this.waiting = false; this.queued = false; this.update({ index: -1, progress: 0, playing: false }); };
  readonly controller: SignAnimationController = {
    play: () => { if (!this.items.length) this.queued = true; else this.begin(0); },
    restart: () => { if (!this.items.length) this.queued = true; else this.begin(0); },
    pause: () => { if (this.state.playing) this.tick(); this.stop(); this.waiting = false; this.queued = false; this.update({ playing: false }); },
    resume: () => {
      if (this.state.index < 0 || this.state.progress >= 1) this.begin(0);
      else { this.waiting = false; this.update({ playing: true }); this.clock(); }
    },
    setSpeed: (speed) => {
      if (![0.5, 1, 1.5].includes(speed)) return;
      if (this.state.playing) this.tick();
      this.update({ speed });
    },
  };
}
