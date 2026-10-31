"""Repository vocabulary selection and validation; no sign/grammar inference."""
import re

from models.translation import LLMResult
from services.english_service import english_words, lemma_candidates
from services.sign_repository import SignRepository, normalize_text

# Existing function glosses, included only when present in this repository.
# This is a prompt retrieval policy, not an assertion about ISL grammar.
CORE_GLOSSES = frozenset({
    "I", "YOU", "WE", "HE", "SHE", "MY", "YOUR", "ME", "NOT", "YES", "NO",
    "WHAT", "WHERE", "WHEN", "WHY", "HOW", "PLEASE", "THANK_YOU",
})
CORE_CATEGORIES = frozenset({"pronoun", "question", "negation", "function"})


def select_vocabulary(text: str, repo: SignRepository, limit: int = 300) -> list[str]:
    """All small vocabularies; otherwise core + best English keyword matches.

    Unknown/unrelated signs do not fill spare slots. Ties sort by gloss so the
    result does not depend on JSON insertion order. Core signs are never evicted
    even if a custom repository has more core entries than the requested limit.
    """
    if limit < 1:
        raise ValueError("Vocabulary limit must be positive")
    signs = {s.gloss: s for s in repo.search("")}
    if len(signs) <= limit:
        return sorted(signs)
    core = {g for g, s in signs.items() if g in CORE_GLOSSES or
            (s.category or "").casefold() in CORE_CATEGORIES}
    words = english_words(text)
    keywords = {normalize_text(word) for word in words}
    for word in words:
        if not word.isdigit():
            keywords.update(lemma_candidates(word.casefold()))
    ranked = []
    normalized_input = f" {normalize_text(text)} "
    for gloss, sign in signs.items():
        if gloss in core:
            continue
        score = 0
        for label in [gloss, *sign.aliases, *([sign.lemma] if sign.lemma else [])]:
            name = normalize_text(label)
            if not name:
                continue
            # Phrase matches outrank single-word lemma/alias matches, which
            # outrank partial overlap with a multiword label.
            score = max(score, 3 if f" {name} " in normalized_input else
                        2 if name in keywords else
                        1 if keywords.intersection(name.split()) else 0)
        if score:
            ranked.append((-score, gloss))
    ranked.sort()
    selected = core | {g for _, g in ranked[:max(0, limit - len(core))]}
    return sorted(selected)


def validate_vocabulary(result: LLMResult, repo: SignRepository,
                        allowed: list[str]) -> LLMResult:
    """Canonicalize aliases, preserve explicit spelling, mark everything else FS.

    Reject malformed spelling payloads so the normal LLM fallback handles them;
    punctuation-only/empty payloads must not become pretend spellable words.
    """
    allowed_set = set(allowed)
    glosses = []
    for detail in result.gloss:
        token = re.sub(r"\s+", "_", detail.gloss.strip()).upper()
        if token.startswith("FS:"):
            if not re.fullmatch(r"FS:\w+(?:[-']\w+)*", token):
                raise ValueError("Invalid FS: token in model output")
            glosses.append(detail.model_copy(update={"gloss": token, "fs": True}))
            continue
        sign = repo.get_by_text(token)
        if sign and sign.gloss in allowed_set:
            glosses.append(detail.model_copy(update={"gloss": sign.gloss, "fs": False}))
        else:
            if not re.fullmatch(r"\w+(?:[-']\w+)*", token):
                raise ValueError("Invalid gloss token in model output")
            glosses.append(detail.model_copy(update={"gloss": f"FS:{token}", "fs": True}))
    return result.model_copy(update={"gloss": glosses})
