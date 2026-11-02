/** Preview scheduling is shared by typed and interim speech text. */
export function scheduleLivePreview(text: string, pausedUntil: number, cancel: () => void, translate: (text: string) => void): () => void {
  cancel();
  if (!text.trim()) return () => {};
  const timer = setTimeout(() => translate(text), Math.max(600, pausedUntil - Date.now()));
  return () => clearTimeout(timer);
}

// WebSocket error event keeps its existing shape; the backend includes Retry-After in its message.
export function liveRetryUntil(message: string): number | null {
  const retry = /Retry-After: (\d+)/.exec(message);
  return retry ? Date.now() + Number(retry[1]) * 1000 : null;
}
