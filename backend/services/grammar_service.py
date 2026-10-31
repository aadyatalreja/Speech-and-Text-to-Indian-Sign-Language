"""Data-driven demo grammar and reviewed example selection; no ISL claims."""
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config import BASE
from models.grammar import GrammarRule, GrammarUse
from models.markers import GlossToken, NonManualMarkers
from models.translation import LLMResult
from services.english_service import english_words
from services.marker_service import load_config
from services.sign_repository import SignRepository, normalize_text

EXAMPLES_PATH = BASE / "data" / "grammar" / "examples.jsonl"


def active_rules(path: Path | None = None) -> list[GrammarRule]:
    return [rule for rule in load_config(path).grammar if rule.enabled and rule.review_decision != "rejected"]


def use(rule: GrammarRule) -> GrammarUse:
    return GrammarUse(**rule.model_dump(include={"id", "source", "review_status", "reviewer"}))


def grammar_notice(uses: list[GrammarUse]) -> str | None:
    draft = sorted({item.id for item in uses if item.review_status != "verified"})
    return "Unverified grammar (demo rules): " + ", ".join(draft) + "." if draft else None


def drop_rule(word: str, rules: list[GrammarRule]) -> GrammarRule | None:
    # Called only after repository lookup failed; never drops a known sign.
    return next((rule for rule in rules if rule.operation == "drop_words" and
                 normalize_text(word) in {normalize_text(w) for w in rule.words}), None)


def apply_grammar(result: LLMResult, text: str, repo: SignRepository,
                  rules: list[GrammarRule]) -> LLMResult:
    tokens = [token.model_copy(deep=True) for token in result.gloss]
    used = list(result.grammar_rules)
    intent = result.intent

    def category(token):
        sign = None if token.fs else repo.get_sign(token.gloss)
        return sign.category if sign else None

    normalized = " ".join(word.casefold() for word in english_words(text))
    input_words = set(normalized.split())
    for rule in rules:
        if rule.operation in {"drop_words", "pending"}:
            continue
        if rule.when_words and not input_words.intersection(word.casefold() for word in rule.when_words):
            continue
        matched = False
        if rule.operation == "phrase":
            expected = " ".join(w.casefold() for w in english_words(rule.english or ""))
            # Existing phrase mappings cannot discard newly matched signs or FS
            # tokens, and cannot introduce glosses missing from the repository.
            if normalized == expected and all(repo.get_sign(g) for g in rule.gloss) and not (
                    Counter(t.gloss for t in tokens) - Counter(rule.gloss)):
                tokens = [GlossToken(gloss=g) for g in rule.gloss]
                intent = rule.intent or intent
                matched = True
        elif rule.operation == "order_categories":
            rank = {value: i for i, value in enumerate(rule.categories)}
            matched = any(category(t) in rank for t in tokens)
            tokens.sort(key=lambda token: rank.get(category(token), rank["rest"]))
        elif rule.operation in {"move_category", "topic_first"}:
            selected = [t for t in tokens if (category(t) == rule.category if rule.operation == "move_category"
                        else result.sentence.topic is not None and normalize_text(t.gloss) == normalize_text(result.sentence.topic))]
            if selected:
                remainder = [t for t in tokens if t not in selected]
                tokens = selected + remainder if rule.operation == "topic_first" or rule.position == "start" else remainder + selected
                matched = True
        elif rule.operation == "repeat":
            matched = rule.count > 1 and any(category(t) == rule.category for t in tokens)
            tokens = [t.model_copy(deep=True) for token in tokens
                      for t in [token] * (rule.count if category(token) == rule.category else 1)]
        elif rule.operation == "pronoun_index":
            for token in tokens:
                if token.gloss in rule.references:
                    token.reference = rule.references[token.gloss]
                    matched = True
        if matched:
            used.append(use(rule))
            # An exact phrase is a complete reviewed/draft mapping; avoid
            # applying generic ordering on top of it.
            if rule.operation == "phrase":
                break
    return result.model_copy(update={"gloss": tokens, "intent": intent,
                                     "sentence": result.sentence.model_copy(update={"intent": intent}),
                                     "grammar_rules": list({item.id: item for item in used}.values())})


class GrammarExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    english: str = Field(min_length=1)
    gloss: list[str] = Field(min_length=1)
    nmm: NonManualMarkers = Field(default_factory=NonManualMarkers)
    reviewer: str | None = None
    review_status: Literal["unverified", "in_review", "verified"]

    @model_validator(mode="after")
    def check_review(self):
        if self.review_status == "verified" and not (self.reviewer or "").strip():
            raise ValueError("Verified examples require a reviewer")
        if not self.english.strip() or any(not token.strip() for token in self.gloss):
            raise ValueError("Example text/gloss must not be blank")
        return self


def verified_examples(allowed: list[str], path: Path | None = None) -> list[GrammarExample]:
    selected = []
    for line_number, line in enumerate((path or EXAMPLES_PATH).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            example = GrammarExample.model_validate(json.loads(line))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid grammar example on line {line_number}: {exc}") from exc
        if example.review_status == "verified" and all(
            token in allowed or (token.startswith("FS:") and token[3:] and
                                 all(ch.isalnum() or ch in "_-'" for ch in token[3:]))
            for token in example.gloss):
            selected.append(example)
    return selected[:50]
