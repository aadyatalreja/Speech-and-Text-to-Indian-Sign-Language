import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import Header from "./components/Header";
import Particles from "./components/Particles";
import TextInput, { type InputMode } from "./components/TextInput";
import ProcessingStatus from "./components/ProcessingStatus";
import TranslationPanel from "./components/TranslationPanel";
import AvatarPanel from "./components/AvatarPanel";
import SignerVideo from "./components/SignerVideo";
import { retimeForAvatar, getClipRevision, subscribeClips } from "./avatar/library";
import { alphabetAssets } from "./avatar/alphabetAssets";
import SignPlayer from "./components/SignPlayer";
import HistoryDrawer, { type HistoryItem } from "./components/HistoryPanel";
import { GlassCard, SectionHeader, SegmentedControl } from "./components/ui";
import { errorMessage, generateVideo, health, streamTranslate, translate } from "./services/api";
import { useSignPlayer } from "./hooks/useSignPlayer";
import { useVideoPlayer } from "./hooks/useVideoPlayer";
import { allVideos, anyVideos, missingVideos } from "./services/videoPlayback";
import { videoLabel } from "./avatar/library";
import { useSpeech } from "./hooks/useSpeech";
import { useTheme } from "./hooks/useTheme";
import type { SignItem, Stage, Translation } from "./types/translation";

const HKEY = "signai.history";
const EXAMPLES = ["Where is the nearest hospital?", "Can you help me?", "I am going to college tomorrow."];
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
  const [videoNote, setVideoNote] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [outputPreference, setOutputPreference] = useState<"video" | "avatar" | null>(null);
  const [streamComplete, setStreamComplete] = useState(true);
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
  const videoPlayer = useVideoPlayer(rawItems);
  const outputMode = outputPreference ?? (streamComplete && allVideos(rawItems) ? "video" : "avatar");
  const player = outputMode === "video" ? videoPlayer : avatarPlayer;
  const playbackItems = outputMode === "video" ? videoPlayer.displayItems : items;
  useEffect(() => {
    if (outputMode === "video") avatarPlayer.controller.pause(); else videoPlayer.controller.pause();
  }, [outputMode]);
  // Speech → text first: the recognised sentence fills the box, then goes through the normal translate flow.
  const speech = useSpeech(lang, (heard) => { setText(heard); run(heard); });
  const busy = stage === "understanding" || stage === "representing" || stage === "preparing";
  const current = player.index >= 0 ? playbackItems[player.index] ?? null : null;

  useEffect(() => { health().then(setOnline); return () => closeWs.current?.(); }, []);

  const save = (list: HistoryItem[]) => { setHistory(list); try { localStorage.setItem(HKEY, JSON.stringify(list)); } catch { /* storage unavailable */ } };
  const remember = (s: string) => save([{ text: s, ts: Date.now() }, ...history.filter((h) => h.text !== s)].slice(0, 20));

  const run = async (input = text) => {
    const clean = input.trim();
    if (!clean) { setError(EMPTY); setStage("error"); return; }
    closeWs.current?.();
    const requestId = ++runId.current;
    setError(null); setVideoNote(null); setVideoUrl(null); setGenerating(false); setOutputPreference(null);
    setStreamComplete(!realtime); setT(null); setItems([]); avatarPlayer.reset(); videoPlayer.reset();
    setStage("understanding");
    remember(clean);
    if (realtime) {
      let meta: Translation | null = null;
      const acc: SignItem[] = [];
      closeWs.current = streamTranslate(clean, (e) => {
        if (requestId !== runId.current) return;
        if (e.type === "understanding") {
          setStage("representing");
          meta = { original_text: clean, target_sign_language: "ISL", intent: e.intent, entities: e.entities, gloss: e.gloss, sequence: [], unknown_signs: [], confidence: e.confidence, engine: e.engine, notice: e.notice };
          meta.gloss_detail = e.gloss_detail; meta.sentence = e.sentence;
          meta.grammar_rules = e.grammar_rules;
          setT(meta);
        } else if (e.type === "sign") {
          acc.push(e.item); setItems([...acc]); setT((p) => p && { ...p, sequence: [...acc] });
          if (e.index === 0) { setStage("ready"); avatarPlayer.controller.play(); }
        } else if (e.type === "done") {
          setT((p) => p && { ...p, unknown_signs: e.unknown_signs });
          setStreamComplete(true);
        } else { setError(e.error); setStage("error"); }
      });
      return;
    }
    try {
      const res = await translate(clean);
      if (requestId !== runId.current) return;
      setStage("preparing"); setT(res); setItems(res.sequence);
      setStage("ready");
    } catch (e) { if (requestId === runId.current) { setError(errorMessage(e)); setStage("error"); } }
  };

  const exportVideo = async () => {
    if (!t) return;
    const requestId = runId.current;
    setGenerating(true); setVideoNote(null); setVideoUrl(null);
    try {
      const result = await generateVideo(t.gloss);
      if (requestId === runId.current) {
        setVideoUrl(result.video_url);
        setVideoNote(result.notice ?? (result.missing_glosses.length ? `Missing signer videos skipped: ${result.missing_glosses.join(", ")}.` : null));
      }
    } catch (e) { if (requestId === runId.current) setVideoNote(errorMessage(e)); }
    finally { if (requestId === runId.current) setGenerating(false); }
  };

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
          <TextInput value={speech.listening ? speech.interim : text} onChange={setText} onTranslate={() => run()} busy={busy} realtime={realtime} onRealtime={setRealtime}
            mode={mode} onMode={(m) => { speech.cancel(); setMode(m); }} speech={speech} lang={lang} onLang={setLang} hint={stage === "error" && error === EMPTY ? EMPTY : null} />
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
                <TranslationPanel t={t} activeIndex={player.index} />
                <GlassCard aria-label="Sign Output" className="p-6">
                  <SectionHeader title="Sign Output" />
                  <div className="mb-4"><SegmentedControl<"video" | "avatar"> label="Sign output mode" value={outputMode}
                    options={[{ value: "video", label: "Real signer videos" }, { value: "avatar", label: "Avatar" }]}
                    disabled={anyVideos(rawItems) ? [] : ["video"]} onChange={(value) => {
                      avatarPlayer.reset(); videoPlayer.reset(); setOutputPreference(value);
                    }} /></div>
                  {outputMode === "video" ? <SignerVideo item={current} items={rawItems} mediaRef={videoPlayer.mediaRef} gap={videoPlayer.phase === "gap"} /> :
                    <AvatarPanel item={current} videoUrl={null} items={items} progress={player.progress} playing={player.playing} />}
                  {outputMode === "video" && missingVideos(rawItems).length > 0 && <p role="status" className="mt-3 text-xs text-warn">No signer video; shown as text: {missingVideos(rawItems).join(", ")}.</p>}
                  {outputMode === "video" && videoPlayer.error && <p role="alert" className="mt-3 text-sm text-warn">{videoPlayer.error}</p>}
                  <SignPlayer items={playbackItems} index={player.index} progress={player.progress} playing={player.playing} speed={player.speed} c={player.controller} />
                  <button className="btn-quiet mt-4" disabled={generating || !streamComplete || !anyVideos(rawItems)} onClick={exportVideo}>
                    {generating ? "Generating video…" : "Generate combined video"}
                  </button>
                  {videoNote && <p role="status" className="mt-3 text-xs text-warn">{videoNote}</p>}
                  {videoUrl && <div className="mt-3"><video src={videoUrl} controls className="aspect-video w-full rounded-card bg-black" aria-label="Combined sign video" />
                    <p className="mt-2 text-center text-xs text-muted">{videoLabel(rawItems)}</p></div>}
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
