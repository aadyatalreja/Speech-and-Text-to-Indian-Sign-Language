"""English coverage fixtures do not assert correctness of ISL grammar."""
import json

import pytest

from services.english_service import english_words, lemma_candidates, resolve_word
from services.llm_service import mock_transform
from services.sequence_service import SignSequenceService
from services.sign_repository import JsonSignRepository, get_repository


@pytest.mark.parametrize("text, expected", [
    ("went to colleges", ["COLLEGE", "GO"]),
    ("Went to colleges", ["COLLEGE", "GO"]),
    ("I am eating", ["I", "EAT"]),
    ("please help me", ["PLEASE", "ME", "HELP"]),
    ("I’m eating", ["I", "EAT"]),
    ("I don't understand", ["I", "UNDERSTAND", "NOT"]),
    ("I can't go", ["I", "GO", "NOT"]),
    ("Priya", ["FS:PRIYA"]),
    ("I see Priya", ["I", "FS:PRIYA", "SEE"]),
    ("0012", ["FS:0", "FS:0", "FS:1", "FS:2"]),
    ("quantum", ["FS:QUANTUM"]),
])
def test_english_coverage(text, expected):
    result = mock_transform(text)
    assert result.flat_gloss == expected
    sequence, unknown = SignSequenceService().build(result.flat_gloss)
    assert [item.gloss for item in sequence] == expected
    assert unknown == [token[3:] for token in expected if token.startswith("FS:")]


def make_repo(tmp_path, entries):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return JsonSignRepository(path)


def test_repository_drives_inflections_entities_and_stop_words(tmp_path):
    repo = make_repo(tmp_path, {
        "LEARN": {"id": "learn", "gloss": "LEARN", "lemma": "study", "category": "verb"},
        "CAMPUS": {"id": "campus", "gloss": "CAMPUS", "aliases": ["college"], "category": "location"},
        "PLEASE": {"id": "please", "gloss": "PLEASE"},
        "CAN": {"id": "can", "gloss": "CAN"},
    })
    result = mock_transform("please can study colleges", repo)
    assert result.flat_gloss == ["PLEASE", "CAN", "CAMPUS", "LEARN"]
    assert [(entity.text, entity.type) for entity in result.entities] == [("colleges", "LOCATION")]
    assert resolve_word("studied", repo).gloss == "LEARN"
    sequence, unknown = SignSequenceService(repo).build(["studied", "colleges"])
    assert [item.gloss for item in sequence] == ["LEARN", "CAMPUS"]
    assert unknown == []


def test_phrases_and_direct_aliases_win(tmp_path):
    repo = make_repo(tmp_path, {
        "GREETING": {"id": "greeting", "gloss": "GREETING", "aliases": ["good morning"]},
        "CUSTOM": {"id": "custom", "gloss": "CUSTOM", "aliases": ["went"]},
        "GO": {"id": "go", "gloss": "GO", "category": "verb"},
    })
    assert mock_transform("Good morning went", repo).flat_gloss == ["GREETING", "CUSTOM"]


def test_number_entries_precede_digit_fallback(tmp_path):
    repo = make_repo(tmp_path, {
        "TWELVE": {"id": "twelve", "gloss": "TWELVE", "aliases": ["12"]},
        "ONE": {"id": "one", "gloss": "ONE", "aliases": ["1"]},
    })
    assert mock_transform("12 101", repo).flat_gloss == ["TWELVE", "ONE", "FS:0", "ONE"]


def test_explicit_fs_never_resolves_as_a_sign():
    sequence, unknown = SignSequenceService().build(["FS:HELLO", "FS:PRIYA"])
    assert unknown == ["HELLO", "PRIYA"]
    assert all(not item.available and item.sign_id is None for item in sequence)


def test_stop_word_only_input_remains_explicit():
    assert mock_transform("the to").flat_gloss == ["FS:THE", "FS:TO"]


def test_capitalized_unknown_does_not_become_a_common_noun(tmp_path):
    repo = make_repo(tmp_path, {"WOOD": {"id": "wood", "gloss": "WOOD"}})
    assert resolve_word("Woods", repo) is None


def test_contraction_tokenization():
    assert english_words("She’s here; we’ve come, they’ll go!") == [
        "She", "is", "here", "we", "have", "come", "they", "will", "go"]


def test_missing_wordnet_has_actionable_error(monkeypatch):
    from services import english_service
    def missing(*args):
        raise LookupError("fixture missing corpus")
    monkeypatch.setattr(english_service._lemmatizer, "lemmatize", missing)
    lemma_candidates.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="nltk.downloader"):
            lemma_candidates("fixtureunknownword")
    finally:
        lemma_candidates.cache_clear()
