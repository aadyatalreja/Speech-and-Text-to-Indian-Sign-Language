import type { Translation } from "../types/translation";
import GlossSequence from "./GlossSequence";
import { GlassCard, SectionHeader } from "./ui";

export default function TranslationPanel({ t, activeIndex }: { t: Translation; activeIndex: number }) {
  const ctx = t.entities.map((e) => e.text[0].toUpperCase() + e.text.slice(1)).join(" · ");
  return (
    <GlassCard aria-label="AI Understanding" className="p-6">
      <SectionHeader title="AI Understanding" />
      <p className="text-lg leading-snug text-ink">“{t.original_text}”</p>
      <dl className="mt-5 space-y-4 text-sm">
        <div><dt className="text-muted">Type</dt><dd className="mt-0.5 text-base font-semibold capitalize">{t.intent}</dd></div>
        {ctx && <div><dt className="text-muted">Context</dt><dd className="mt-0.5 text-base font-semibold">{ctx}</dd></div>}
        <div><dt className="mb-2 text-muted">Sign sequence</dt><dd><GlossSequence items={t.sequence} activeIndex={activeIndex} /></dd></div>
      </dl>
      {t.unknown_signs.length > 0 && (
        <div role="alert" className="mt-5 rounded-ctl bg-warn-soft p-4 text-sm text-warn">
          <p className="font-semibold">Some signs aren’t available yet</p>
          <p className="mt-1 font-bold">{t.unknown_signs.join(", ")}</p>
          <p className="mt-1">The remaining sequence can still be played.</p>
        </div>
      )}
      <div className="mt-5 space-y-1 text-xs text-muted">
        {t.engine === "api" ? <p>Translation confidence · {Math.round(t.confidence * 100)}%</p> : <p>Processed with built-in fallback rules, not a language model.</p>}
        {t.notice && t.unknown_signs.length === 0 && <p>{t.notice}</p>}
        <p>The sign sequence is an intermediate representation, not an authoritative ISL translation.</p>
      </div>
    </GlassCard>
  );
}
