import { useEffect, useMemo, useSyncExternalStore } from "react";
import type { SignItem } from "../types/translation";
import { TimelinePlayback } from "../services/timelinePlayback";

/** Preserve the existing hook/controller interface with a testable base-time clock. */
export function useSignPlayer(items: SignItem[]) {
  const playback = useMemo(() => new TimelinePlayback(), []);
  const state = useSyncExternalStore(playback.subscribe, playback.getSnapshot);
  useEffect(() => { playback.setItems(items); }, [items, playback]);
  useEffect(() => () => playback.controller.pause(), [playback]);
  return { ...state, controller: playback.controller, reset: playback.reset };
}
