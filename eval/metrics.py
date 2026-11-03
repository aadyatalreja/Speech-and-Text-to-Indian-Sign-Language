"""Metrics arithmetic only. Synthetic tests are not ISL or comprehension evidence."""

from collections import Counter
from itertools import combinations
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DISCLAIMER = "Gloss agreement/accuracy is not comprehension accuracy, naturalness, or verified ISL quality. Repository coverage includes unverified demos; verified asset coverage is separate."
CONTENT_POLICY = "English token occurrences excluding the explicit function-word list; optional reviewer-provided content_words override this heuristic. A word is covered only if all tokens from its deterministic lookup resolve to repository signs. No verified-asset claim."
FUNCTION_WORDS = set(
    "a an the i me my mine you your yours he him his she her hers it its we us our ours they them their theirs this that these those am is are was were be been being do does did have has had can could will would shall should may might must to of for in on at with from by and but or as if than then there here please".split()
)


class Judgement(BaseModel):
    reviewer: str  # Consented study pseudonym; identity key stays private.
    gloss_acceptable: Literal["yes", "no", "uncertain"] | None = None
    nmm_correct: Literal["yes", "no", "uncertain"] | None = None
    comprehension: int | None = Field(default=None, ge=1, le=5, strict=True)
    comments: str = ""
    signed_off: bool = False

    @model_validator(mode="after")
    def attributed(self):
        if self.signed_off and not self.reviewer.strip():
            raise ValueError("Signed judgement requires reviewer attribution")
        return self


def edit_distance(reference, predicted):
    previous = list(range(len(predicted) + 1))
    for i, token in enumerate(reference, 1):
        current = [i]
        for j, candidate in enumerate(predicted, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (token != candidate))
            )
        previous = current
    return previous[-1]


def content_coverage(text, repo, words=None):
    from services.english_service import english_words
    from services.llm_service import mock_transform

    tokens = (
        words
        if words is not None
        else [w for w in english_words(text) if w.casefold() not in FUNCTION_WORDS]
    )
    resolved = 0
    for word in tokens:
        result = mock_transform(word, repo)
        resolved += bool(result.gloss) and all(
            not t.fs and repo.get_by_text(t.gloss) for t in result.gloss
        )
    return {
        "content_words": len(tokens),
        "resolved_content_words": resolved,
        "content_word_coverage": resolved / len(tokens) if tokens else None,
    }


def cohen_kappa(pairs):
    """Unweighted nominal Cohen kappa on complete paired ratings."""
    if not pairs:
        return {"kappa": None, "reason": "no paired items", "items": 0}
    left, right = zip(*pairs)
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    a, b = Counter(left), Counter(right)
    chance = sum(a[c] * b[c] for c in a.keys() | b.keys()) / n**2
    return {
        "kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
        "reason": None if chance < 1 else "degenerate marginals (chance agreement is 1)",
        "items": n,
        "observed_agreement": observed,
        "chance_agreement": chance,
    }


def fleiss_kappa(items):
    """Unweighted Fleiss kappa: fixed number of distinct raters per item."""
    if not items:
        return {"kappa": None, "reason": "no complete items", "items": 0}
    raters = len(items[0])
    if raters < 2 or any(len(item) != raters for item in items):
        raise ValueError("Fleiss kappa requires a fixed number >=2 of ratings per item")
    n = len(items)
    counts = [Counter(item) for item in items]
    observed = (
        sum(sum(v * (v - 1) for v in row.values()) / (raters * (raters - 1)) for row in counts) / n
    )
    totals = sum(counts, Counter())
    chance = sum((count / (n * raters)) ** 2 for count in totals.values())
    return {
        "kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
        "reason": None if chance < 1 else "degenerate marginals (chance agreement is 1)",
        "items": n,
        "raters_per_item": raters,
        "observed_agreement": observed,
        "chance_agreement": chance,
    }


def reviewer_agreement(rows):
    """Only signed ratings on eligible verified rows; no imputed missing ratings."""
    eligible = [
        r
        for r in rows
        if r.review_status == "verified" and not r.placeholder and (r.reviewer or "").strip()
    ]
    output = {}
    for field in ("gloss_acceptable", "nmm_correct", "comprehension"):
        ratings = []
        for row in eligible:
            item = {}
            for judgement in row.judgements:
                if not judgement.signed_off or getattr(judgement, field) is None:
                    continue
                if judgement.reviewer in item:
                    raise ValueError(
                        "Duplicate reviewer rating on an item; adjudicate revisions before scoring"
                    )
                item[judgement.reviewer] = getattr(judgement, field)
            ratings.append(item)
        reviewers = sorted({r for item in ratings for r in item})
        # Pseudonyms are not included in public metric summaries.
        pairwise = [
            cohen_kappa([(item[a], item[b]) for item in ratings if a in item and b in item])
            for a, b in combinations(reviewers, 2)
        ]
        sizes = Counter(len(item) for item in ratings if len(item) >= 2)
        target = max(sizes, key=lambda k: (sizes[k], k)) if sizes else None
        complete = (
            [list(item.values()) for item in ratings if len(item) == target] if target else []
        )
        output[field] = {
            "pairwise_cohen": pairwise,
            "fleiss": fleiss_kappa(complete),
            "excluded_incomplete_or_different_rater_count": len(ratings) - len(complete),
            "definition": "Unweighted nominal kappa; Likert scores are treated as categories, not interval measurements. Missing/unsigned ratings are excluded.",
        }
    return output
