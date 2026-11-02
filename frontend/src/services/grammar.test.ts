import { expect, it } from "vitest";
import { unverifiedGrammar } from "./grammar";
import type { GrammarUse } from "../types/translation";

it("keeps each draft grammar label until that specific rule is verified", () => {
  const rules: GrammarUse[] = [
    { id: "draft_order", source: "synthetic fixture", review_status: "unverified", reviewer: null },
    { id: "draft_drop", source: "synthetic fixture", review_status: "in_review", reviewer: null },
  ];
  expect(unverifiedGrammar(rules)).toEqual(["draft_drop", "draft_order"]);
  expect(unverifiedGrammar([{ ...rules[0], review_status: "verified" }, rules[1]])).toEqual(["draft_drop"]);
  expect(unverifiedGrammar()).toEqual([]);
});
