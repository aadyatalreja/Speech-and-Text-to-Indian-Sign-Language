import { GlassCard, SegmentedControl } from "./ui";
export type InputMode = "type" | "speak";
export interface SpeechState { supported: boolean; listening: boolean; error: string | null; start: () => void; stop: () => void }
const LANGS = [["en-IN", "English (India)"], ["en-US", "English (US)"], ["en-GB", "English (UK)"]];

interface Props {
  value: string; onChange: (v: string) => void; onTranslate: () => void; busy: boolean;
  realtime: boolean; onRealtime: (v: boolean) => void; mode: InputMode; onMode: (m: InputMode) => void;
  speech: SpeechState; lang: string; onLang: (l: string) => void; hint: string | null;
}

export default function TextInput(p: Props) {
  const { speech } = p;
  return (
    <div id="top">
      <GlassCard className="p-6 sm:p-7">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <label htmlFor="text" className="font-display text-lg font-semibold tracking-tight">What would you like to translate?</label>
          <SegmentedControl label="Input method" value={p.mode} onChange={p.onMode} disabled={speech.supported ? [] : ["speak"]}
            options={[{ value: "type", label: "Type" }, { value: "speak", label: "Speak" }]} />
        </div>
        <textarea id="text" rows={3} maxLength={500} value={p.value} readOnly={speech.listening}
          placeholder={p.mode === "speak" ? "Your spoken sentence appears here…" : "Type a sentence, question, or phrase…"}
          onChange={(e) => p.onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) p.onTranslate(); }}
          className="w-full resize-none rounded-ctl border border-line/10 bg-surface/60 p-4 text-lg leading-relaxed outline-none transition placeholder:text-muted/70 focus:border-accent/60 focus:bg-surface/80 focus:ring-4 focus:ring-accent/20" />
        <div className="mt-2 flex items-center justify-between text-xs text-muted">
          <span>English → ISL{!speech.supported && " · Speech input needs Chrome, Edge or Safari"}</span>
          <span aria-live="polite">{p.value.length} / 500</span>
        </div>
      </GlassCard>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
        {p.mode === "speak" && (
          <>
            <button className={p.speech.listening ? "btn-primary" : "btn bg-raised/70 text-ink ring-1 ring-line/10 hover:bg-raised"} aria-pressed={speech.listening}
              onClick={speech.listening ? speech.stop : speech.start} disabled={p.busy}>
              {speech.listening ? "■ Stop listening" : "🎤 Start speaking"}
            </button>
            <label className="sr-only" htmlFor="lang">Speech language</label>
            <select id="lang" className="rounded-ctl bg-raised/70 px-3 py-2.5 text-sm ring-1 ring-line/10" value={p.lang} onChange={(e) => p.onLang(e.target.value)} disabled={speech.listening}>
              {LANGS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
            </select>
          </>
        )}
        <button className="btn-primary px-6" onClick={p.onTranslate} disabled={p.busy || speech.listening}>Translate to ISL →</button>
        <button className="btn-quiet" onClick={() => p.onChange("")} disabled={!p.value || speech.listening}>Clear</button>
        <SegmentedControl label="Output mode" value={p.realtime ? "rt" : "video"} onChange={(v) => p.onRealtime(v === "rt")}
          options={[{ value: "video", label: "Video" }, { value: "rt", label: "Real-time" }]} />
      </div>
      <div className="mt-3 min-h-6 text-center text-sm" role="status" aria-live="polite">
        {speech.listening && <span className="inline-flex items-center gap-2 font-medium text-accent-fg"><span className="h-2.5 w-2.5 animate-pulse rounded-full bg-accent" />Listening… speak your sentence</span>}
        {p.hint && !speech.listening && <span role="alert" className="font-medium text-warn">{p.hint}</span>}
        {speech.error && <span role="alert" className="font-medium text-warn">{speech.error}</span>}
      </div>
    </div>
  );
}