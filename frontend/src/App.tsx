import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import Header from "./components/Header";
import Particles from "./components/Particles";
import TextInput, { type InputMode } from "./components/TextInput";
import ProcessingStatus from "./components/ProcessingStatus";
import TranslationPanel from "./components/TranslationPanel";
import AvatarPanel from "./components/AvatarPanel";
import { retimeForAvatar, getClipRevision, subscribeClips } from "./avatar/library";
import { alphabetAssets } from "./avatar/alphabetAssets";
import SignPlayer from "./components/SignPlayer";
import HistoryDrawer, { type HistoryItem } from "./components/HistoryPanel";
import { GlassCard, SectionHeader, SegmentedControl } from "./components/ui";
import { errorMessage, health, streamTranslate, translate } from "./services/api";
import { useSignPlayer } from "./hooks/useSignPlayer";
import { scheduleLivePreview, liveRetryUntil } from "./services/livePreview";
import { useSpeech } from "./hooks/useSpeech";
import { useTheme } from "./hooks/useTheme";
import type { SignItem, Stage, Translation } from "./types/translation";
import { CHARACTERS, isCharacterId, type CharacterId } from "./avatar/characters";

const HKEY = "signai.history";
const EXAMPLES = ["Where is the nearest hospital?", "Can you help me?", "I am going to college tomorrow.", "I am going to the hospital tomorrow morning.", "Please help me, where is the doctor?"];
const EMPTY = "Please enter a sentence.";
const loadHistory = (): HistoryItem[] => {
  try {
    const raw = JSON.parse(localStorage.getItem(HKEY) ?? "[]") as (string | HistoryItem)[];
    return raw.map((r) => (typeof r === "string" ? { text: r, ts: Date.now() } : r)); // older entries were plain strings
  } catch { return []; }
};

export default function App() {
  const [text, setText] = useState("");
  const [realtime, setRealtime] = useState(false);
  const [mode, setMode] = useState<InputMode>("type");
  const [lang, setLang] = useState("en-IN");
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [character, setCharacter] = useState<CharacterId>(() => {
    try {
      const saved = localStorage.getItem("signai.character");
      return saved === "female" ? "anya" : isCharacterId(saved) ? saved : "arav";   // "female" = older saved value
    } catch { return "arav"; }
  });
  const pickCharacter = (value: CharacterId) => {
    setCharacter(value);
    try { localStorage.setItem("signai.character", value); } catch { /* storage unavailable */ }
  };
  const [streamComplete, setStreamComplete] = useState(true);
  const [pausedUntil, setPausedUntil] = useState(0);
  const lastFinal = useRef("");
  const pendingFinal = useRef<string | null>(null);
  const runId = useRef(0);
  const [t, setT] = useState<Translation | null>(null);
  const [rawItems, setItems] = useState<SignItem[]>([]);
  // fingerspelled glosses get longer timing so each letter is readable
  const alphabetRevision = useSyncExternalStore(alphabetAssets.subscribe, alphabetAssets.getRevision);
  const clipRevision = useSyncExternalStore(subscribeClips, getClipRevision);
  const items = useMemo(() => retimeForAvatar(rawItems), [rawItems, alphabetRevision, clipRevision]);
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory);
  const [drawer, setDrawer] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const { dark, toggle: toggleTheme } = useTheme();
  const closeWs = useRef<(() => void) | null>(null);
  const avatarPlayer = useSignPlayer(items);
  const player = avatarPlayer;
  const playbackItems = items;
  const [reviewTranscript, setReviewTranscript] = useState(false);
  const invalidate = () => {
    ++runId.current;
    closeWs.current?.();
    pendingFinal.current = null;
    avatarPlayer.reset();
    setT(null); setItems([]); setStage("idle"); setError(null);
  };
  const speech = useSpeech(lang, (heard) => {
    setText(heard.slice(0, 500));
    setReviewTranscript(true);
  });
  useEffect(() => {
    if (speech.error && !speech.interim.trim()) setReviewTranscript(false);
  }, [speech.error, speech.interim]);

  const changeText = (value: string) => {
    invalidate();
    lastFinal.current = "";
    setText(value);
  };
  const busy = stage === "understanding" || stage === "representing" || stage === "preparing";
  const current = player.index >= 0 ? playbackItems[player.index] ?? null : null;

  useEffect(() => { health().then(setOnline); return () => closeWs.current?.(); }, []);

  const save = (list: HistoryItem[]) => { setHistory(list); try { localStorage.setItem(HKEY, JSON.stringify(list)); } catch { /* storage unavailable */ } };
  const remember = (s: string) => save([{ text: s, ts: Date.now() }, ...history.filter((h) => h.text !== s)].slice(0, 20));

  const run = async (input = text, preview = false, inputLanguage = lang) => {
    const clean = input.trim();
    if (!clean) { setError(EMPTY); setStage("error"); return; }
    if (!preview) {
      speech.cancel();
      setReviewTranscript(false);
      lastFinal.current = clean;
      remember(clean);
    }
    if (realtime && Date.now() < pausedUntil) {
      if (!preview) pendingFinal.current = clean;
      return;
    }
    pendingFinal.current = null;
    closeWs.current?.();
    const requestId = ++runId.current;
    setError(null);
    setStreamComplete(!realtime); setT(null); setItems([]); avatarPlayer.reset();
    setStage("understanding");
    if (realtime) {
      let meta: Translation | null = null;
      const acc: SignItem[] = [];
      closeWs.current = streamTranslate(clean, (e) => {
        if (requestId !== runId.current) return;
        if (e.type === "understanding") {
          setStage("representing");
          meta = { original_text: clean, english_text: e.english_text, target_sign_language: "ISL", intent: e.intent, entities: e.entities, gloss: e.gloss, sequence: [], unknown_signs: [], confidence: e.confidence, engine: e.engine, notice: e.notice };
          meta.gloss_detail = e.gloss_detail; meta.sentence = e.sentence;
          meta.grammar_rules = e.grammar_rules;
          setT(meta);
        } else if (e.type === "sign") {
          acc.push(e.item); setItems([...acc]); setT((p) => p && { ...p, sequence: [...acc] });
          if (e.index === 0) { setStage("ready"); avatarPlayer.controller.play(); }
        } else if (e.type === "done") {
          setT((p) => p && { ...p, unknown_signs: e.unknown_signs });
          setStreamComplete(true);
        } else {
          const retry = liveRetryUntil(e.error);
          if (retry !== null) {
            if (!preview) pendingFinal.current = clean;
            setPausedUntil(retry);
          }
          setError(e.error); setStage("error");
        }
      }, inputLanguage);
      return;
    }
    try {
      const res = await translate(clean, inputLanguage);
      if (requestId !== runId.current) return;
      setStage("preparing"); setT(res); setItems(res.sequence);
      setStage("ready");
    } catch (e) { if (requestId === runId.current) { setError(errorMessage(e)); setStage("error"); } }
  };

  const latestRun = useRef(run);
  latestRun.current = run;
  useEffect(() => {
    if (!realtime || speech.listening || reviewTranscript || text.trim() === lastFinal.current) return;
    return scheduleLivePreview(text, pausedUntil, () => {
      ++runId.current;
      closeWs.current?.();
    }, (value) => { void latestRun.current(value, true); });
  }, [text, realtime, pausedUntil, speech.listening, reviewTranscript, lang]);
  useEffect(() => {
    if (!pausedUntil) return;
    const timer = window.setTimeout(() => {
      setPausedUntil(0); setError(null); setStage("idle");
      const final = pendingFinal.current;
      if (final) { pendingFinal.current = null; void latestRun.current(final); }
    }, Math.max(0, pausedUntil - Date.now()));
    return () => window.clearTimeout(timer);
  }, [pausedUntil]);

  const pick = (s: string) => { setText(s); run(s); };
  const hardError = stage === "error" && error && error !== EMPTY;

  return (
    <MotionConfig reducedMotion="user">
      <Particles dark={dark} />
      <Header onHistory={() => setDrawer(true)} online={online} dark={dark} onToggleTheme={toggleTheme} />
      <main className="relative mx-auto max-w-5xl px-4 pb-24 pt-14 sm:pt-20">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .35 }}>
          <div className="mb-10 text-center">
            <p className="mb-4 inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-accent-fg"><span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />EXPERIMENTAL SIGN PLAYBACK</p>
            <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-6xl">Turn words into signs.</h1>
            <p className="mx-auto mt-3 max-w-md text-base text-muted">Explore English-to-gloss playback · experimental, not verified ISL.</p>
          </div>
          <TextInput value={speech.listening ? speech.interim : text} onChange={changeText} onTranslate={() => { if (!speech.listening) void run(); }} busy={busy} realtime={realtime} onRealtime={setRealtime}
            mode={mode} onMode={(m) => { speech.cancel(); setReviewTranscript(false); setMode(m); }} speech={{ ...speech, start: () => { invalidate(); setReviewTranscript(true); speech.start(); } }} lang={lang} onLang={(value) => { invalidate(); lastFinal.current = ""; setLang(value); }} hint={stage === "error" && error === EMPTY ? EMPTY : null} />
          {reviewTranscript && !speech.listening && (!speech.error || speech.interim.trim()) && <p className="mt-2 text-sm text-muted" role="status">Review or edit the transcript, then select Preview sign sequence.</p>}
          {realtime && <p className="mt-2 text-xs text-muted" role="status">{pausedUntil > Date.now() ? `Live paused by rate limit until ${new Date(pausedUntil).toLocaleTimeString()}.` : "Live previews typed text · Speech waits for your review."}</p>}
        </motion.div>

        <div className="mt-14" aria-live="polite">
          <AnimatePresence mode="wait">
            {busy && !t ? (
              <motion.div key="busy" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><ProcessingStatus stage={stage} /></motion.div>
            ) : hardError ? (
              <motion.div key="err" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <GlassCard className="mx-auto max-w-md p-7 text-center" role="alert">
                  <h2 className="text-lg font-semibold text-warn">Couldn’t translate that sentence</h2>
                  <p className="mt-2 text-sm text-muted">{error}</p>
                  <button className="btn-primary mt-5" onClick={() => run()}>Try again</button>
                </GlassCard>
              </motion.div>
            ) : t ? (
              <motion.div key="result" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: .3 }} className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
                <TranslationPanel t={t} activeIndex={player.index} onCorrectEnglish={(english) => { setText(english); setLang("en-IN"); void run(english, false, "English"); }} />
                <GlassCard aria-label="Sign Output" className="p-6">
                  <SectionHeader title="Sign Output" aside={
                    <label className="flex items-center gap-2 text-xs font-medium text-muted">
                      Signer
                      <select value={character} onChange={e => pickCharacter(e.target.value as CharacterId)}
                        className="rounded-ctl border border-line/15 bg-raised px-3 py-1.5 text-sm font-semibold text-ink shadow-sm focus:outline-none focus:ring-2 focus:ring-accent/40">
                        {CHARACTERS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    </label>} />
                  <AvatarPanel item={current} videoUrl={null} items={items} progress={player.progress} playing={player.playing} character={character} />
                  <SignPlayer items={playbackItems} index={player.index} progress={player.progress} playing={player.playing} speed={player.speed} c={player.controller} />
                </GlassCard>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center">
                <h2 className="font-display text-2xl font-semibold tracking-tight">Translate your first sentence</h2>
                <p className="mx-auto mt-2 max-w-sm text-sm text-muted">Type something above to preview a demo gloss and sign sequence.</p>
                <p className="mb-3 mt-8 text-xs text-muted">Try an example</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((e) => <button key={e} onClick={() => pick(e)} disabled={busy} className="chip">“{e}”</button>)}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
      <HistoryDrawer open={drawer} items={history} onPick={pick} onClear={() => save([])} onClose={() => setDrawer(false)} />
    </MotionConfig>
  );
}
