import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import TranslationPanel, { tokenDiagnostic } from "../components/TranslationPanel";
import type { GlossToken, Translation } from "../types/translation";

const token: GlossToken = { gloss: "FS:BOUGHT", fs: true, nmm: {}, nmm_rules: [], nmm_verified: false, fs_reason: "oov", lemma_tried: "buy" };

it("renders an accessible muted explanation for an OOV token", () => {
  const t: Translation = { original_text: "bought", target_sign_language: "ISL", intent: "statement", entities: [], gloss: [token.gloss], gloss_detail: [token], sequence: [], unknown_signs: [], confidence: 0.6, engine: "mock", notice: null };
  const html = renderToStaticMarkup(<TranslationPanel t={t} activeIndex={-1} />);
  expect(html).toContain('aria-label="Token diagnostics"');
  expect(html).toContain("no sign in repository; tried lemma &#x27;buy&#x27;");
});

it("explains names, model unknowns, explicit spelling and substitutions", () => {
  expect(tokenDiagnostic({ ...token, fs_reason: "name_heuristic", lemma_tried: null })).toBe("kept as a possible name");
  expect(tokenDiagnostic({ ...token, fs_reason: "model_unknown" })).toContain("unknown model gloss");
  expect(tokenDiagnostic({ ...token, fs_reason: "explicit" })).toContain("explicitly supplied");
  expect(tokenDiagnostic({ ...token, fs_reason: null, synonym_from: "purchase" })).toContain("meaning may drift");
});
