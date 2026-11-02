import { describe, expect, it, vi } from "vitest";
import { configureClientIp } from "./devProxy";

describe("development proxy client IP", () => {
  it("overwrites spoofed forwarding headers for HTTP and WebSocket", () => {
    const handlers = new Map<string, (...args: any[]) => void>();
    const proxy = { on: vi.fn((event, handler) => handlers.set(event, handler)) };
    configureClientIp(proxy as any, {});
    for (const event of ["proxyReq", "proxyReqWs"]) {
      const outgoing = { setHeader: vi.fn() };
      handlers.get(event)!(outgoing, { socket: { remoteAddress: "192.0.2.1" }, headers: { "x-forwarded-for": "spoofed" } });
      expect(outgoing.setHeader).toHaveBeenCalledWith("X-Forwarded-For", "192.0.2.1");
    }
  });
});
