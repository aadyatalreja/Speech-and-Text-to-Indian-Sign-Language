import { useCallback, useEffect, useRef, useState } from "react";

// Web Speech API is not in TypeScript's DOM lib, so the parts we use are typed here.
export interface Recognition {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  start(): void; stop(): void; abort(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}
export type RecognitionConstructor = new () => Recognition;
const recognitionConstructor = (): RecognitionConstructor | undefined =>
  typeof window === "undefined" ? undefined : (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

export const ERRORS: Record<string, string> = {
  unavailable: "Speech recognition is unavailable in this browser. Please type instead.",
  "language-not-supported": "Speech recognition does not support the selected language in this browser. Please type instead.",
  "language-unavailable": "Speech recognition is unavailable for the selected language. Please type instead.",
  "not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type instead.",
  "service-not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type instead.",
  "no-speech": "No speech heard. Press the microphone and try again.",
  "audio-capture": "No microphone found. Connect one, or type instead.",
  network: "The speech service could not be reached. Check your internet connection, or type instead.",
};

/** Shared recognizer wiring, also exercised with a fake browser recognizer. */
export function createSpeechSession(Ctor: RecognitionConstructor, lang: string, callbacks: {
  interim: (text: string) => void; final: (text: string) => void;
  error: (message: string) => void; end: () => void;
}) {
  const r = new Ctor();
  let finalText = "";
  let finished = false;
  r.lang = lang; r.interimResults = true; r.continuous = false; r.maxAlternatives = 1;
  r.onresult = e => {
    if (finished) return;
    finalText = "";
    let interimText = "";
    for (let i = 0; i < e.results.length; i++) {
      const part = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += part; else interimText += part;
    }
    callbacks.interim(finalText + interimText);
  };
  r.onerror = e => {
    if (finished) return;
    finished = true;
    callbacks.end();
    if (e.error !== "aborted") callbacks.error(ERRORS[e.error] ?? "Speech recognition failed. Please type instead.");
  };
  r.onend = () => {
    if (finished) return;
    finished = true;
    callbacks.end();
    if (finalText.trim()) callbacks.final(finalText);
    else callbacks.error(ERRORS["no-speech"]);
  };
  return { recognition: r, cancel: () => { if (finished) return; finished = true; r.abort(); } };
}

/** Speech -> text, preserving the recognizer's Unicode transcript. */
export function useSpeech(lang: string, onFinal: (text: string) => void) {
  const Ctor = recognitionConstructor();
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const session = useRef<ReturnType<typeof createSpeechSession> | null>(null);
  const cb = useRef(onFinal);
  cb.current = onFinal;

  const start = useCallback(() => {
    if (!Ctor) { setError(ERRORS.unavailable); return; }
    session.current?.cancel();
    setError(null); setInterim("");
    try {
      const next = createSpeechSession(Ctor, lang, {
        interim: setInterim, final: text => cb.current(text),
        error: setError, end: () => setListening(false),
      });
      session.current = next;
      setListening(true);
      next.recognition.start();
    } catch (cause) {
      session.current?.cancel(); setListening(false);
      setError(cause instanceof DOMException && cause.name === "NotSupportedError"
        ? ERRORS["language-not-supported"] : "Speech recognition could not start. Please type instead.");
    }
  }, [Ctor, lang]);

  const stop = useCallback(() => { session.current?.recognition.stop(); }, []);
  const cancel = useCallback(() => { session.current?.cancel(); setListening(false); setInterim(""); }, []);
  useEffect(() => { setError(null); return () => session.current?.cancel(); }, [lang]);
  return { supported: Boolean(Ctor), listening, interim, error: error ?? (!Ctor ? ERRORS.unavailable : null), start, stop, cancel };
}
