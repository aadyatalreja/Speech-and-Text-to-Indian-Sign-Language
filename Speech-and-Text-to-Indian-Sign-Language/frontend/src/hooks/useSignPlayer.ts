import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SignAnimationController, SignItem } from "../types/translation";

/** Timer-driven controller. Swap the consumer (AvatarPanel) for a Three.js avatar without touching this. */
export function useSignPlayer(items: SignItem[]) {
  const [index, setIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeedState] = useState(1);
  const [progress, setProgress] = useState(0);
  const start = useRef(0);
  const carried = useRef(0);

  useEffect(() => {
    if (!playing || index < 0) return;
    const item = items[index];
    if (!item) { setPlaying(false); return; }
    const total = (item.duration + item.pause_after) * 1000 / speed;
    start.current = performance.now();
    const tick = window.setInterval(() => {
      const p = Math.min(1, carried.current + (performance.now() - start.current) / total);
      setProgress(p);
      if (p >= 1) {
        window.clearInterval(tick);
        carried.current = 0;
        if (index + 1 < items.length) { setProgress(0); setIndex(index + 1); }
        else setPlaying(false); // waits for more streamed items if any arrive
      }
    }, 50);
    return () => { window.clearInterval(tick); carried.current = Math.min(1, carried.current + (performance.now() - start.current) / total); };
  }, [playing, index, speed, items]);

  // Resume automatically when a streamed sign arrives after playback caught up.
  const finished = useRef(false);
  useEffect(() => { finished.current = !playing && index >= 0 && index === items.length - 1 && progress >= 1; }, [playing, index, items.length, progress]);
  useEffect(() => { if (finished.current && index + 1 < items.length) { carried.current = 0; setProgress(0); setIndex(index + 1); setPlaying(true); } }, [items.length]); // eslint-disable-line

  const controller: SignAnimationController = useMemo(() => ({
    play: () => { carried.current = 0; setProgress(0); setIndex(0); setPlaying(true); },
    pause: () => setPlaying(false),
    resume: () => { if (index < 0) { setIndex(0); } setPlaying(true); },
    restart: () => { carried.current = 0; setProgress(0); setIndex(0); setPlaying(true); },
    setSpeed: (s: number) => setSpeedState(s),
  }), [index]);

  const reset = useCallback(() => { setPlaying(false); setIndex(-1); setProgress(0); carried.current = 0; }, []);
  return { index, playing, speed, progress, controller, reset };
}
