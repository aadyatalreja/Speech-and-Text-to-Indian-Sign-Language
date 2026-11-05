"""English lexical normalization only; does not define ISL grammar or signs."""

import re
from functools import lru_cache

from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

from models.sign import Sign
from services.sign_repository import SignRepository

_lemmatizer = WordNetLemmatizer()
SMALL_NUMBERS = dict(
    zip(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(),
        range(20),
    )
)
TENS = dict(
    zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10))
)
SCALES = {
    "thousand": 10**3,
    "lakh": 10**5,
    "million": 10**6,
    "crore": 10**7,
    "billion": 10**9,
    "trillion": 10**12,
}
_UNIT = "|".join(list(SMALL_NUMBERS)[1:10])
_SMALL = "|".join(sorted(SMALL_NUMBERS, key=len, reverse=True))
_TENS = "|".join(TENS)
_UNDER_HUNDRED = rf"(?:(?:{_TENS})(?:[ -](?:{_UNIT}))?|(?:{_SMALL}))"
_GROUP = rf"(?:(?:(?:{_UNIT}) +)?hundred(?: +(?:and +)?{_UNDER_HUNDRED})?|{_UNDER_HUNDRED})"
_SCALED = [rf"(?:{_GROUP} +)?{scale}" for scale in reversed(SCALES)]
# Require decreasing scales, allowing omitted intermediate groups.
_NUMBER_PHRASE = re.compile(
    r"\b(?:"
    + "|".join(
        first
        + "".join(rf"(?: +{later})?" for later in _SCALED[index + 1 :])
        + rf"(?: +(?:and +)?{_GROUP})?"
        for index, first in enumerate(_SCALED)
    )
    + rf"|{_GROUP})\b",
    re.IGNORECASE,
)


def normalize_number_words(text: str) -> str:
    """Turn English cardinal phrases into digits while preserving surrounding text."""

    def replace(match):
        total = 0
        group = None
        for word in match[0].lower().replace("-", " ").split():
            if word in SCALES:
                total += (1 if group is None else group) * SCALES[word]
                group = None
            elif word == "hundred":
                group = (1 if group is None else group) * 100
            elif word != "and":
                group = (group or 0) + SMALL_NUMBERS.get(word, TENS.get(word, 0))
        return str(total + (group or 0))

    return _NUMBER_PHRASE.sub(replace, text)


_CONTRACTIONS = {
    "can't": "can not",
    "cannot": "can not",
    "won't": "will not",
    "shan't": "shall not",
    "let's": "let us",
}


def english_words(text: str) -> list[str]:
    text = text.replace("’", "'")
    for short, expanded in _CONTRACTIONS.items():
        text = re.sub(r"\b" + re.escape(short) + r"\b", expanded, text, flags=re.I)
    # Expand auxiliary contractions, preserving the case of the subject/name.
    text = re.sub(r"n't\b", " not", text, flags=re.I)
    for suffix, expanded in [
        ("'m", " am"),
        ("'re", " are"),
        ("'ve", " have"),
        ("'ll", " will"),
        ("'d", " would"),
    ]:
        text = re.sub(re.escape(suffix) + r"\b", expanded, text, flags=re.I)
    # 's is ambiguous (possessive/is/has): expand only common pronoun forms.
    text = re.sub(r"\b(he|she|it|that|there|what|who)'s\b", r"\1 is", text, flags=re.I)
    return re.findall(
        r"(?:[^\W\d_]|[\u0900-\u0963\u0c80-\u0ce3])+(?:'[^\W\d_]+)*|\d+", text, flags=re.UNICODE
    )


@lru_cache(maxsize=2048)
def lemma_candidates(word: str) -> tuple[str, ...]:
    """Try verb and noun forms; repository membership resolves candidates."""
    lower = word.casefold()
    try:
        return tuple(
            dict.fromkeys(_lemmatizer.lemmatize(lower, pos) for pos in ("v", "n", "a", "r"))
        )
    except LookupError as exc:
        raise RuntimeError(
            "NLTK WordNet data is missing. Run: python -m nltk.downloader wordnet "
            "(see README for the project-local data directory)."
        ) from exc


def resolve_word(word: str, repo: SignRepository) -> Sign | None:
    """Original gloss/alias/lemma first, then English inflection candidates."""
    sign = repo.get_by_text(word)
    if sign or word.isdigit():
        return sign
    # Unknown capitalized words are kept intact for fingerspelling; do not
    # turn a potential name such as 'Woods' into the common noun 'wood'.
    if word[:1].isupper():
        return None
    for lemma in lemma_candidates(word):
        sign = repo.get_by_text(lemma)
        if sign:
            return sign
    return None


def number_tokens(word: str, repo: SignRepository) -> list[str]:
    """Prefer a whole-number entry, otherwise resolve each digit independently."""
    sign = repo.get_by_text(word)
    if sign:
        return [sign.gloss]
    return [sign.gloss if (sign := repo.get_by_text(digit)) else f"FS:{digit}" for digit in word]


def tried_lemma(word: str) -> str:
    candidates = lemma_candidates(word.casefold())
    return next((lemma for lemma in candidates if lemma != word.casefold()), word.casefold())


def potential_name(word: str, index: int) -> bool:
    """Conservative capitalization heuristic, not named-entity recognition."""
    if not word[:1].isupper() or word.isupper():
        return False
    return index > 0 or not wordnet.synsets(word.casefold())


@lru_cache(maxsize=2048)
def synonym_candidates(word: str) -> tuple[str, ...]:
    """One-hop WordNet lexical neighbours, not sign equivalence or disambiguation."""
    synsets = wordnet.synsets(word.casefold())
    neighbours = [*synsets, *(parent for item in synsets for parent in item.hypernyms())]
    return tuple(
        dict.fromkeys(
            lemma.name().replace("_", " ")
            for item in neighbours
            for lemma in sorted(item.lemmas(), key=lambda item: item.name())
        )
    )[:128]


def synonym_match(word: str, repo: SignRepository) -> Sign | None:
    return next(
        (
            sign
            for candidate in synonym_candidates(word)
            if (sign := repo.get_by_text(candidate)) and sign.review_decision != "rejected"
        ),
        None,
    )
