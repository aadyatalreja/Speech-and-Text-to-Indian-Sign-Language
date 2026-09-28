import axios from "axios";
import type { SignItem, Translation } from "../types/translation";

const http = axios.create({ baseURL: "/api", timeout: 30000 });

export function errorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data;
    if (typeof d?.error === "string") return d.error;
    if (typeof d?.detail === "string") return d.detail;
    if (e.response?.status === 422) return "Please enter a sentence.";
  }
  return "Translation service temporarily unavailable.";
}

export const translate = (text: string) =>
  http.post<Translation>("/translate", { text, source_language: "English", target_sign_language: "ISL" }).then((r) => r.data);

export const generateVideo = (sequence: string[]) =>
  http.post<{ video_url: string }>("/generate-video", { sequence }).then((r) => r.data.video_url);

type StreamEvent =
  | { type: "understanding"; intent: string; entities: Translation["entities"]; gloss: string[]; confidence: number; engine: string; notice: string | null }
  | { type: "sign"; index: number; item: SignItem }
  | { type: "done"; unknown_signs: string[] }
  | { type: "error"; error: string };

/** Real-time mode: signs arrive one by one so playback can start before the last sign is sent. */
export function streamTranslate(text: string, onEvent: (e: StreamEvent) => void): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/api/translate/stream`);
  ws.onopen = () => ws.send(JSON.stringify({ text }));
  ws.onmessage = (m) => onEvent(JSON.parse(m.data));
  ws.onerror = () => onEvent({ type: "error", error: "Translation service temporarily unavailable." });
  return () => ws.close();
}
