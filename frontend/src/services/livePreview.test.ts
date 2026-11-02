import { afterEach, expect, it, vi } from "vitest";
import { liveRetryUntil, scheduleLivePreview } from "./livePreview";

afterEach(() => vi.useRealTimers());
it("debounces latest typed or speech text and cancels active previews immediately", () => {
  vi.useFakeTimers();
  const cancel = vi.fn(), run = vi.fn();
  const cleanup = scheduleLivePreview("I", 0, cancel, run);
  expect(cancel).toHaveBeenCalledTimes(1);
  vi.advanceTimersByTime(500);
  cleanup();
  scheduleLivePreview("I need help", 0, cancel, run);
  vi.advanceTimersByTime(599);
  expect(run).not.toHaveBeenCalled();
  vi.advanceTimersByTime(1);
  expect(run).toHaveBeenCalledOnce();
  expect(run).toHaveBeenCalledWith("I need help");
  expect(cancel).toHaveBeenCalledTimes(2);
});
it("waits for Retry-After and cancels pending work when cleared", () => {
  vi.useFakeTimers();
  vi.setSystemTime(1000);
  const until = liveRetryUntil("Rate limit exceeded. Retry-After: 3")!;
  expect(until).toBe(4000);
  expect(liveRetryUntil("Other error")).toBeNull();
  const run = vi.fn();
  scheduleLivePreview("latest interim", until, vi.fn(), run);
  vi.advanceTimersByTime(2999);
  expect(run).not.toHaveBeenCalled();
  vi.advanceTimersByTime(1);
  expect(run).toHaveBeenCalledOnce();
  const cleanup = scheduleLivePreview("discarded", 0, vi.fn(), run);
  cleanup();
  scheduleLivePreview(" ", 0, vi.fn(), run);
  vi.advanceTimersByTime(1000);
  expect(run).toHaveBeenCalledOnce();
});
