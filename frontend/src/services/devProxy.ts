import type { ProxyOptions } from "vite";

/** The Compose backend trusts this proxy, so discard client-supplied forwarding headers. */
export const configureClientIp: NonNullable<ProxyOptions["configure"]> = (proxy) => {
  proxy.on("proxyReq", (outgoing, incoming) => outgoing.setHeader("X-Forwarded-For", incoming.socket.remoteAddress ?? ""));
  proxy.on("proxyReqWs", (outgoing, incoming) => outgoing.setHeader("X-Forwarded-For", incoming.socket.remoteAddress ?? ""));
};
