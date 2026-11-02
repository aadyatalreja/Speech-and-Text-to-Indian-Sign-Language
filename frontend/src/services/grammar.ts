import type { GrammarUse } from "../types/translation";

/** Each draft influence remains visible until that specific rule is reviewed. */
export function unverifiedGrammar(rules: GrammarUse[] = []): string[] {
  return [...new Set(rules.filter((rule) => rule.review_status !== "verified").map((rule) => rule.id))].sort();
}
