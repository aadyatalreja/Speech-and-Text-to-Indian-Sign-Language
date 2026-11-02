import { useEffect, useMemo, useRef, useSyncExternalStore } from "react";
import type { SignItem } from "../types/translation";
import { VideoPlayback } from "../services/videoPlayback";

export function useVideoPlayer(items: SignItem[]) {
  const playback = useMemo(() => new VideoPlayback(), []);
  const media = useRef<HTMLVideoElement | null>(null);
  const state = useSyncExternalStore(playback.subscribe, playback.getSnapshot);
  useEffect(() => { playback.setItems(items); }, [items, playback]);
  const mediaRef = useMemo(() => (element: HTMLVideoElement | null) => { media.current = element; playback.attach(element); }, [playback]);
  useEffect(() => {
    playback.attach(media.current);
    return () => { playback.controller.pause(); playback.attach(null); };
  }, [playback]);
  return { ...state, controller: playback.controller, reset: playback.reset, mediaRef, displayItems: playback.displayItems() };
}
