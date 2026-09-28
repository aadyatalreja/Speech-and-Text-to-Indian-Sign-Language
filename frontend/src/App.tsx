import { useEffect, useMemo, useRef, useState } from "react";
import Header from "./components/Header";
import TextInput, { type InputMode } from "./components/TextInput";
import ProcessingStatus from "./components/ProcessingStatus";
import TranslationPanel from "./components/TranslationPanel";
import AvatarPanel from "./components/AvatarPanel";
import SignPlayer from "./components/SignPlayer";
import HistoryPanel from "./components/HistoryPanel";
import { errorMessage, generateVideo, streamTranslate, translate } from "./services/api";
import { useSignPlayer } from "./hooks/useSignPlayer";
import { useSpeech } from "./hooks/useSpeech";
import type { SignItem, Stage, Translation } from "./types/translation";

const HKEY = "signai.history";
const loadHistory = (): string[] => { try { return JSON.parse(localStorage.getItem(HKEY) ?? "[]"); } catch { return []; } };

export default function App() {
  const [text, setText] = useState("");
  const [realtime, setRealtime] = useState(false);
  const [mode, setMode] = useState<InputMode>("type");
  const [lang, setLang] = useState("en-IN");
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [videoNote, setVideoNote] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [t, setT] = useState<Translation | null>(null);
  const [items, setItems] = useState<SignItem[]>([]);
  const [history, setHistory] = useState<string[]>(loadHistory);
  const closeWs = useRef<(() => void) | null>(null);
  const player = useSignPlayer(items);
  // Speech → text first: the recognised sentence fills the box, then goes through the normal translate flow.
  const speech = useSpeech(lang, (heard) => { setText(heard); run(heard); });
  const busy = stage === "understanding" || stage === "representing" || stage === "preparing";
  const current = player.index >= 0 ? items[player.index] ?? null : null;

  useEffect(() => () => closeWs.current?.(), []);

  const remember = (s: string) => {
    const next = [s, ...history.filter((h) => h !== s)].slice(0, 8);
    setHistory(next);
    try { localStorage.setItem(HKEY, JSON.stringify(next)); } catch { /* storage unavailable */ }
  };

  const run = async (input = text) => {
    const clean = input.trim();
    if (!clean) { setError("Please enter a sentence."); setStage("error"); return; }
    closeWs.current?.();
    setError(null); setVideoNote(null); setVideoUrl(null); setT(null); setItems([]); player.reset();
    setStage("understanding");
    remember(clean);
    if (realtime) {
      let meta: Translation | null = null;
      const acc: SignItem[] = [];
      closeWs.current = streamTranslate(clean, (e) => {
        if (e.type === "understanding") {
          setStage("representing");
          meta = { original_text: clean, target_sign_language: "ISL", intent: e.intent, entities: e.entities, gloss: e.gloss, sequence: [], unknown_signs: [], confidence: e.confidence, engine: e.engine, notice: e.notice };
          setT(meta);
        } else if (e.type === "sign") {
          acc.push(e.item); setItems([...acc]); setT((p) => p && { ...p, sequence: [...acc] });
          if (e.index === 0) { setStage("ready"); player.controller.play(); }
        } else if (e.type === "done") {
          setT((p) => p && { ...p, unknown_signs: e.unknown_signs, notice: e.unknown_signs.length ? "Some signs are currently unavailable." : p.notice });
        } else { setError(e.error); setStage("error"); }
      });
      return;
    }
    try {
      const res = await translate(clean);
      setStage("preparing"); setT(res); setItems(res.sequence);
      try { setVideoUrl(await generateVideo(res.gloss)); } catch { setVideoNote("Video generation failed. The sign sequence is still available."); }
      setStage("ready");
    } catch (e) { setError(errorMessage(e)); setStage("error"); }
  };

  const glossItems = useMemo(() => items, [items]);
  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <TextInput value={speech.listening ? speech.interim : text} onChange={setText} onTranslate={() => run()} busy={busy} realtime={realtime} onRealtime={setRealtime}
          mode={mode} onMode={(m) => { speech.cancel(); setMode(m); }} speech={speech} lang={lang} onLang={setLang} />
        <ProcessingStatus stage={stage} />
        {error && <p role="alert" className="rounded-lg border-2 border-ink bg-saffron p-3 font-bold">{error}</p>}
        <div className="grid gap-6 lg:grid-cols-2">
          <TranslationPanel t={t} activeIndex={player.index} />
          <div>
            <AvatarPanel item={current} playing={player.playing} videoUrl={videoUrl} />
            {videoNote && <p className="mt-2 text-base">{videoNote}</p>}
            <SignPlayer items={glossItems} index={player.index} progress={player.progress} playing={player.playing} speed={player.speed} c={player.controller} />
          </div>
        </div>
        {t && <section aria-label="Transcript" className="rounded-xl border-2 border-line p-5"><h2 className="font-bold">Transcript</h2><p>{t.original_text}</p><p className="mt-1">Gloss: {t.gloss.join(" ")}</p></section>}
        <HistoryPanel items={history} onPick={(h) => { setText(h); run(h); }} />
      </main>
    </>
  );
}
