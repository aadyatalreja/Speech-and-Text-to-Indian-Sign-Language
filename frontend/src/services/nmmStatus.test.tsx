import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import NmmStatus from "../components/NmmStatus";
import TranslationPanel from "../components/TranslationPanel";
import type { SignItem, Translation } from "../types/translation";

const item: SignItem = { gloss: "WHERE", sign_id: "where", available: true, duration: 1, pause_after: 0.2, asset_type: "demo", video_url: null, nmm: { brow: 0.55 }, nmm_rules: ["question_nmm_pending_review"], nmm_verified: false };

it("shows current expression rule IDs and an accessible unverified badge", () => {
  const html = renderToStaticMarkup(<NmmStatus item={item} />);
  expect(html).toContain('role="status"');
  expect(html).toContain("question_nmm_pending_review");
  expect(html).toContain("demo expression, not signer-verified");
});

it("uses the current sign in the translation panel and leaves missing provenance unverified", () => {
  const t: Translation = { original_text: "Where?", target_sign_language: "ISL", intent: "question", entities: [], gloss: ["WHERE"], sequence: [item], unknown_signs: [], confidence: 0.6, engine: "mock", notice: null };
  expect(renderToStaticMarkup(<TranslationPanel t={t} activeIndex={0} />)).toContain("question_nmm_pending_review");
  const html = renderToStaticMarkup(<NmmStatus item={{ ...item, nmm_rules: [], nmm_verified: undefined }} />);
  expect(html).toContain("none active");
  expect(html).toContain("not signer-verified");
  expect(renderToStaticMarkup(<NmmStatus item={null} />)).toBe("");
});
