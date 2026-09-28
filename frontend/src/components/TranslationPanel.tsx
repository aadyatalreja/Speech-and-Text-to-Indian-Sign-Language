import type { Translation } from "../types/translation";
import GlossSequence from "./GlossSequence";
interface Props { t: Translation | null; activeIndex: number }
export default function TranslationPanel({ t, activeIndex }: Props) {
  if (!t) return <section className="rounded-xl border-2 border-line p-5"><p>Translate a sentence to see how it is understood and turned into signs.</p></section>;
  const engineNote = t.engine === "api" ? "Language model" : "Fallback rules (no language model)";
  return (
    <section aria-label="AI understanding" className="rounded-xl border-2 border-ink bg-panel p-5">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="font-bold">Original</dt><dd>{t.original_text}</dd>
        <dt className="font-bold">Intent</dt><dd className="capitalize">{t.intent}</dd>
        <dt className="font-bold">Entities</dt><dd>{t.entities.length ? t.entities.map((e) => `${e.text} (${e.type.toLowerCase()})`).join(", ") : "None found"}</dd>
        <dt className="font-bold">Confidence</dt><dd>{Math.round(t.confidence * 100)}%</dd>
        <dt className="font-bold">Processed by</dt><dd>{engineNote}</dd>
      </dl>
      <h2 className="mb-2 mt-5 font-bold">Sign gloss</h2>
      <GlossSequence items={t.sequence} activeIndex={activeIndex} />
      {t.unknown_signs.length > 0 && <p className="mt-3 font-bold" role="alert">⚠ Sign unavailable: {t.unknown_signs.join(", ")}</p>}
      {t.notice && <p className="mt-2 text-base">{t.notice}</p>}
      <p className="mt-4 text-sm">The gloss is a computational intermediate form, not an authoritative ISL translation.</p>
    </section>
  );
}
