"""Small, unverified lexical baseline and deterministic ASCII transliteration."""

import json
import re
import unicodedata
from pathlib import Path

from services.file_cache import cached_file
from config import settings

LEXICON_DIR = Path(__file__).parents[1] / "data/lexicon"
GLOSSARY_NOTICE = "demo glossary, machine-assembled, not linguist-verified"
ROMANIZATION_NOTICE = (
    "Unmapped Indic words were romanized/transliterated for character spelling. "
    "Character playback depends on available clips and avatar poses."
)


def language_code(language: str) -> str | None:
    return {
        "hi": "hi",
        "hi-in": "hi",
        "hindi": "hi",
        "kn": "kn",
        "kn-in": "kn",
        "kannada": "kn",
    }.get(language.strip().casefold())


def has_indic(text: str) -> bool:
    return any("\u0900" <= c <= "\u097f" or "\u0c80" <= c <= "\u0cff" for c in text)


def lexical_english(text: str, language: str) -> tuple[str, str]:
    code = language_code(language)
    if code is None:
        return text, "No demo glossary for this language; original tokens preserved."
    if not settings.ENABLE_DEMO_INDIC_GLOSSARY:
        return (
            text,
            GLOSSARY_NOTICE + ". Glossary disabled; all original tokens preserved and unmapped.",
        )
    glossary = cached_file(LEXICON_DIR / f"{code}_en.json", json.loads)["entries"]
    # Letters and combining marks stay together. Punctuation has no lexical role.
    tokens = re.findall(r"[^\s.,!?;:।…]+", unicodedata.normalize("NFC", text))
    unmapped = [token for token in tokens if has_indic(token) and token not in glossary]
    english = " ".join(glossary.get(token, token) for token in tokens)
    notice = GLOSSARY_NOTICE + ". Word lookup only; English word order is not reconstructed."
    if unmapped:
        notice += " Unmapped tokens preserved: " + ", ".join(dict.fromkeys(unmapped)) + "."
    return english or text, notice


def romanize(text: str) -> str:
    """Project ASCII abugida scheme: inherent a, no Hindi schwa deletion.

    Shared Unicode block offsets cover basic Devanagari and Kannada. Long
    vowels double; retroflex/dental and nasal distinctions are intentionally
    collapsed. Unlisted characters use U<hex>, never disappear silently.
    """
    vowels = {
        5: "a",
        6: "aa",
        7: "i",
        8: "ii",
        9: "u",
        10: "uu",
        11: "ri",
        12: "li",
        14: "e",
        15: "e",
        16: "ai",
        18: "o",
        19: "o",
        20: "au",
    }
    marks = {
        0x3E: "aa",
        0x3F: "i",
        0x40: "ii",
        0x41: "u",
        0x42: "uu",
        0x43: "ri",
        0x44: "rii",
        0x46: "e",
        0x47: "e",
        0x48: "ai",
        0x4A: "o",
        0x4B: "o",
        0x4C: "au",
    }
    consonants = dict(
        zip(
            range(0x15, 0x3A),
            "k kh g gh ng ch chh j jh ny t th d dh n t th d dh n n p ph b bh m y r r l l l v sh sh s h".split(),
        )
    )
    chars = [
        c
        for c in unicodedata.normalize("NFC", text)
        if c not in {"\u093c", "\u0cbc", "\u200c", "\u200d"}
    ]
    out = []
    for i, char in enumerate(chars):
        base = (
            0x900
            if "\u0900" <= char <= "\u097f"
            else 0xC80
            if "\u0c80" <= char <= "\u0cff"
            else None
        )
        if base is None:
            out.append(char if char.isascii() and char.isalnum() else f"U{ord(char):04X}")
            continue
        offset = ord(char) - base
        next_offset = ord(chars[i + 1]) - base if i + 1 < len(chars) else None
        if offset in consonants:
            out.append(
                consonants[offset] + ("" if next_offset in marks or next_offset == 0x4D else "a")
            )
        elif offset in vowels:
            out.append(vowels[offset])
        elif offset in marks:
            out.append(marks[offset])
        elif offset in (0, 1, 2):
            out.append("m")
        elif offset == 3:
            out.append("h")
        elif offset == 0x4D:
            pass
        elif char.isdecimal():
            out.append(str(unicodedata.decimal(char)))
        else:
            out.append(f"U{ord(char):04X}")
    return "".join(out).upper()
