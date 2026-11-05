import { useEffect, useState } from "react";
import type { GlossToken, Translation } from "../types/translation";
import GlossSequence from "./GlossSequence";
import { GlassCard, SectionHeader } from "./ui";
import NmmStatus from "./NmmStatus";

// Hide two boilerplate sentences from the displayed notice; other notices stay visible.
export function displayNotice(notice: string | null | undefined): string {
  return (notice ?? "")
    .replace("Machine-translated to English first; not verified.", "")
    .replace(/Unverified grammar \(demo rules\):[^.]*\./, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function tokenDiagnostic(token: GlossToken): string {
  const parts: string[] = [];
  if (token.fs_reason) parts.push({
    oov: "no sign in repository",
    name_heuristic: "kept as a possible name",
    model_unknown: "unknown model gloss",
    explicit: "explicitly supplied for spelling",
  }[token.fs_reason]);
  if (token.lemma_tried) parts.push(`tried lemma '${token.lemma_tried}'`);
  if (token.synonym_from) parts.push(`substituted from '${token.synonym_from}' — meaning may drift`);
  return parts.join("; ");
}

export default function TranslationPanel({ t, activeIndex, onCorrectEnglish }: { t: Translation; activeIndex: number; onCorrectEnglish?: (text: string) => void }) {
  const [english, setEnglish] = useState(t.english_text ?? t.original_text);
  useEffect(() => setEnglish(t.english_text ?? t.original_text), [t.english_text, t.original_text]);
  const ctx = t.entities.map((e) => e.text[0].toUpperCase() + e.text.slice(1)).join(" · ");
  return (
    <GlassCard aria-label="AI Understanding" className="p-6">
      <SectionHeader title="AI Understanding" />
      <p className="text-lg leading-snug text-ink">“{t.original_text}”</p>
      {t.english_text != null && (t.english_text !== t.original_text || t.notice?.includes("Machine-translated")) && <div className="mt-3 text-sm">
        <label htmlFor="english-intermediate">English intermediate · experimental</label>
        <textarea id="english-intermediate" maxLength={500} value={english} onChange={e => setEnglish(e.target.value)} className="mt-1 w-full rounded border border-line/20 bg-transparent p-2" />
        <button className="btn-quiet" disabled={!english.trim()} onClick={() => onCorrectEnglish?.(english)}>Correct and re-run in English</button>
      </div>}
      <dl className="mt-5 space-y-4 text-sm">
        <div><dt className="text-muted">Type</dt><dd className="mt-0.5 text-base font-semibold capitalize">{t.intent}</dd></div>
        {t.sentence && <div><dt className="text-muted">Sentence metadata · English analysis</dt><dd>
          {t.sentence.question_type ? `Question: ${t.sentence.question_type}` : "No question detected"}
          {t.sentence.negated ? " · Negation detected" : ""}
          {t.sentence.topic ? ` · Topic: ${t.sentence.topic}` : ""}
        </dd></div>}
        {ctx && <div><dt className="text-muted">Context</dt><dd className="mt-0.5 text-base font-semibold">{ctx}</dd></div>}
        <div><dt className="mb-2 text-muted">Sign sequence</dt><dd><GlossSequence items={t.sequence} activeIndex={activeIndex} sentence={t.original_text} /></dd></div>
      </dl>
      <div className="mt-3"><NmmStatus item={t.sequence[activeIndex]} /></div>
      {t.gloss_detail?.some(token => tokenDiagnostic(token)) && <ul aria-label="Token diagnostics" className="mt-3 space-y-1 text-xs text-muted">
        {t.gloss_detail.map((token, index) => {
          const diagnostic = tokenDiagnostic(token);
          return diagnostic ? <li key={index}>{token.gloss}: {diagnostic}</li> : null;
        })}
      </ul>}
      {t.unknown_signs.length > 0 && (
        <div role="alert" className="mt-5 rounded-ctl bg-warn-soft p-4 text-sm text-warn">
          <p className="font-semibold">Some signs aren’t available yet</p>
          <p className="mt-1 font-bold">{t.unknown_signs.join(", ")}</p>
          <p className="mt-1">The avatar fingerspells words without a playable sign. Spelling is labeled in the player.</p>
        </div>
      )}
      <div className="mt-5 space-y-1 text-xs text-muted">
        {t.engine.startsWith("mock") && <p>Processed with built-in fallback rules.</p>}
      </div>
    </GlassCard>
  );
}
