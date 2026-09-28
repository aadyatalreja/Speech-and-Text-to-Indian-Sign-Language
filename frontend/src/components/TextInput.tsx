export type InputMode = "type" | "speak";
export interface SpeechState { supported: boolean; listening: boolean; error: string | null; start: () => void; stop: () => void }

interface Props {
  value: string; onChange: (v: string) => void; onTranslate: () => void; busy: boolean;
  realtime: boolean; onRealtime: (v: boolean) => void;
  mode: InputMode; onMode: (m: InputMode) => void;
  speech: SpeechState; lang: string; onLang: (l: string) => void;
}

const LANGS = [["en-IN", "English (India)"], ["en-US", "English (US)"], ["en-GB", "English (UK)"]];

export default function TextInput({ value, onChange, onTranslate, busy, realtime, onRealtime, mode, onMode, speech, lang, onLang }: Props) {
  const tab = (m: InputMode, label: string, disabled = false) => (
    <button role="radio" aria-checked={mode === m} disabled={disabled} onClick={() => onMode(m)}
      className={`border-2 border-ink px-4 py-2 font-bold first:rounded-l-lg last:rounded-r-lg disabled:opacity-40 ${mode === m ? "bg-ink text-paper" : "bg-panel"}`}>
      {label}
    </button>
  );
  return (
    <section aria-labelledby="in-h" className="rounded-xl border-2 border-ink bg-panel p-5">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 id="in-h" className="font-bold">Input</h2>
        <div role="radiogroup" aria-labelledby="in-h" className="flex">
          {tab("type", "Type")}
          {tab("speak", "Speak", !speech.supported)}
        </div>
        {!speech.supported && <span className="text-sm">Speech input needs Chrome, Edge or Safari.</span>}
      </div>

      <label htmlFor="text" className="sr-only">Sentence to translate</label>
      <textarea id="text" rows={3} maxLength={500} value={value} readOnly={speech.listening}
        placeholder={mode === "speak" ? "Your spoken sentence appears here…" : "Type your sentence here…"}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onTranslate(); }}
        className="w-full resize-none rounded-lg border-2 border-line p-3 text-xl" />

      <div className="mt-3 flex flex-wrap items-center gap-3">
        {mode === "speak" && (
          <>
            <button className={`btn ${speech.listening ? "bg-ink text-paper" : "bg-saffron hover:bg-[#ffc233]"}`} aria-pressed={speech.listening}
              onClick={speech.listening ? speech.stop : speech.start} disabled={busy}>
              {speech.listening ? "■ Stop listening" : "Start speaking"}
            </button>
            <label className="flex items-center gap-2">Language
              <select className="rounded-lg border-2 border-ink bg-panel px-2 py-2" value={lang} onChange={(e) => onLang(e.target.value)} disabled={speech.listening}>
                {LANGS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
              </select>
            </label>
          </>
        )}
        <button className={`btn ${mode === "type" ? "bg-saffron hover:bg-[#ffc233]" : ""}`} onClick={onTranslate} disabled={busy || speech.listening}>Translate</button>
        <button className="btn" onClick={() => onChange("")} disabled={!value || speech.listening}>Clear</button>
        <label className="ml-2 flex items-center gap-2">
          <input type="checkbox" className="h-5 w-5" checked={realtime} onChange={(e) => onRealtime(e.target.checked)} />
          Real-time mode
        </label>
        <span className="ml-auto text-base" aria-live="polite">{value.length}/500</span>
      </div>

      <p role="status" aria-live="polite" className="mt-2 min-h-6 font-bold">
        {speech.listening && <><span className="mr-2 inline-block h-3 w-3 animate-pulse rounded-full bg-ink align-middle" />Listening… speak your sentence</>}
      </p>
      {speech.error && <p role="alert" className="mt-1 rounded-lg border-2 border-ink bg-saffron p-2 font-bold">{speech.error}</p>}
      <p className="mt-1 text-sm">
        {mode === "speak"
          ? "Your speech is converted to text first, then translated. You can edit the text and translate again. In Chrome, audio is processed by an online speech service."
          : "Ctrl+Enter translates."}
      </p>
    </section>
  );
}
