"""English lexical normalization only; does not define ISL grammar or signs."""
import re
from functools import lru_cache

from nltk.stem import WordNetLemmatizer

from models.sign import Sign
from services.sign_repository import SignRepository

_lemmatizer = WordNetLemmatizer()
_CONTRACTIONS = {
    "can't": "can not", "cannot": "can not", "won't": "will not",
    "shan't": "shall not", "let's": "let us",
}


def english_words(text: str) -> list[str]:
    text = text.replace("’", "'")
    for short, expanded in _CONTRACTIONS.items():
        text = re.sub(r"\b" + re.escape(short) + r"\b", expanded, text, flags=re.I)
    # Expand auxiliary contractions, preserving the case of the subject/name.
    text = re.sub(r"n't\b", " not", text, flags=re.I)
    for suffix, expanded in [("'m", " am"), ("'re", " are"), ("'ve", " have"),
                             ("'ll", " will"), ("'d", " would")]:
        text = re.sub(re.escape(suffix) + r"\b", expanded, text, flags=re.I)
    # 's is ambiguous (possessive/is/has): expand only common pronoun forms.
    text = re.sub(r"\b(he|she|it|that|there|what|who)'s\b", r"\1 is", text, flags=re.I)
    return re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)*|\d+", text, flags=re.UNICODE)


@lru_cache(maxsize=2048)
def lemma_candidates(word: str) -> tuple[str, ...]:
    """Try verb and noun forms; repository membership resolves candidates."""
    lower = word.casefold()
    try:
        return tuple(dict.fromkeys(_lemmatizer.lemmatize(lower, pos) for pos in ("v", "n", "a", "r")))
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
