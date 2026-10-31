"""Apply only configured NMM mappings, never guessed or model-authored poses."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from config import BASE
from models.markers import NonManualMarkers, SentenceMetadata
from models.translation import LLMResult
from models.grammar import GrammarRule
from services.english_service import english_words

RULES_PATH = BASE / "data" / "grammar" / "isl_rules.yaml"


class Conditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: str | None = None
    question_type: Literal["wh", "yes_no"] | None = None
    negated: bool | None = None
    topic: str | None = None


class MarkerRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    review_status: Literal["unverified", "in_review", "verified"]
    enabled: bool = False
    needs_signer_review: bool = True
    when: Conditions
    span: Literal["sentence", "gloss"] = "sentence"
    glosses: list[str] = Field(default_factory=list)
    nmm: NonManualMarkers = Field(default_factory=NonManualMarkers)
    reviewer: str | None = None
    review_decision: Literal["verified", "rejected"] | None = None
    review_history: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_rule(self):
        if not self.id.strip() or not self.source.strip():
            raise ValueError("Rule id and source must not be blank")
        if self.span == "gloss" and not self.glosses:
            raise ValueError("Gloss span requires glosses")
        if self.enabled and not self.nmm.model_dump(exclude_none=True):
            raise ValueError("Enabled marker rule requires numeric nmm channels")
        return self


class MarkerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    rules: list[MarkerRule] = Field(default_factory=list)
    grammar: list[GrammarRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [rule.id for rule in [*self.rules, *self.grammar]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate marker rule ids")
        return self


def load_rules(path: Path | None = None) -> list[MarkerRule]:
    return load_config(path).rules


def load_config(path: Path | None = None) -> MarkerConfig:
    # Read each request so disabling a rule takes effect without restart.
    data = yaml.safe_load((path or RULES_PATH).read_text(encoding="utf-8"))
    return MarkerConfig.model_validate(data)


def apply_markers(result: LLMResult, text: str, path: Path | None = None) -> tuple[LLMResult, str | None]:
    words = {word.casefold() for word in english_words(text)}
    question = result.intent == "question" or text.rstrip().endswith("?")
    sentence = SentenceMetadata(
        intent="question" if question else result.intent,
        question_type=("wh" if words & {"what", "where", "when", "why", "how", "who", "which"}
                       else "yes_no") if question else None,
        negated=bool(words & {"not", "never", "no"}), topic=result.sentence.topic)
    # Model output can carry the structure, but cannot bypass rule review by
    # providing arbitrary NMM values or a claimed verification flag.
    tokens = [token.model_copy(update={"nmm": NonManualMarkers(), "nmm_rules": [],
                                       "nmm_verified": False}) for token in result.gloss]
    unverified = set()
    for rule in load_rules(path):
        if not rule.enabled or rule.review_decision == "rejected":
            continue
        conditions = rule.when.model_dump(exclude_none=True)
        if not all(getattr(sentence, key) == value for key, value in conditions.items()):
            continue
        verified = rule.review_status == "verified" and not rule.needs_signer_review
        for token in tokens:
            if rule.span == "gloss" and token.gloss not in rule.glosses:
                continue
            values = {**token.nmm.model_dump(exclude_none=True), **rule.nmm.model_dump(exclude_none=True)}
            token.nmm = NonManualMarkers(**values)
            token.nmm_verified = verified and (not token.nmm_rules or token.nmm_verified)
            token.nmm_rules.append(rule.id)
            if not verified:
                unverified.add(rule.id)
    notice = ("Demo / not verified ISL non-manual markers: " + ", ".join(sorted(unverified)) + ".") if unverified else None
    return result.model_copy(update={"gloss": tokens, "sentence": sentence, "intent": sentence.intent}), notice
