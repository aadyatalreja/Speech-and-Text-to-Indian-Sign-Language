import { useCallback, useEffect, useRef, useState } from "react";

// Web Speech API is not in TypeScript's DOM lib, so the parts we use are typed here.
interface Recognition {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  start(): void; stop(): void; abort(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}
const Ctor: (new () => Recognition) | undefined =
  typeof window === "undefined" ? undefined : (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

const ERRORS: Record<string, string> = {
  "not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type instead.",
  "service-not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type instead.",
  "no-speech": "No speech heard. Press the microphone and try again.",
  "audio-capture": "No microphone found. Connect one, or type instead.",
  network: "The speech service could not be reached. Check your internet connection, or type instead.",
};

/** Speech → text. Calls onFinal once with the recognised sentence when the person stops speaking. */
export function useSpeech(lang: string, onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<Recognition | null>(null);
  const finalText = useRef("");
  const cb = useRef(onFinal);
  cb.current = onFinal;

  const start = useCallback(() => {
    if (!Ctor) return;
    setError(null); setInterim(""); finalText.current = "";
    const r = new Ctor();
    r.lang = lang; r.interimResults = true; r.continuous = false; r.maxAlternatives = 1;
    r.onresult = (e) => {
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const part = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText.current += part; else interimText += part;
      }
      setInterim((finalText.current + interimText).trim());
    };
    r.onerror = (e) => { if (e.error !== "aborted") setError(ERRORS[e.error] ?? "Speech recognition failed. Try again, or type instead."); };
    r.onend = () => {
      setListening(false);
      const heard = finalText.current.trim();
      if (heard) cb.current(heard);
    };
    rec.current = r;
    try { r.start(); setListening(true); } catch { setError("Speech recognition could not start. Try again."); }
  }, [lang]);

  const stop = useCallback(() => { rec.current?.stop(); }, []);
  const cancel = useCallback(() => { finalText.current = ""; rec.current?.abort(); setListening(false); setInterim(""); }, []);
  useEffect(() => () => rec.current?.abort(), []);

  return { supported: Boolean(Ctor), listening, interim, error, start, stop, cancel };
}
