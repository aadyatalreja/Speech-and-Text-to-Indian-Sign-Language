"""English-only coverage diagnostics; synthetic fixtures are not ISL references."""

import asyncio
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app
from models.markers import GlossToken
from services import english_service, llm_service
from services.sign_repository import JsonSignRepository
from tools.coverage_report import build_report, main, markdown


FILTER_WORDS = "and but or for in on at with from by this that these those there here as if".split()


@pytest.fixture
def vocabulary_gaps(tmp_path, monkeypatch):
    """Keep diagnostic gaps explicit as the production vocabulary grows."""
    source = Path(__file__).parents[1] / "data/signs/signs.json"
    entries = json.loads(source.read_text(encoding="utf-8"))
    for gloss in ("BUY", "VEGETABLE", "NEAR"):
        entries.pop(gloss)
    path = tmp_path / "signs.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    repo = JsonSignRepository(path)
    monkeypatch.setattr(llm_service, "get_repository", lambda: repo)


@pytest.mark.parametrize("word", FILTER_WORDS)
def test_demo_english_filter_words(word):
    result = llm_service.mock_transform(f"hello {word} water")
    assert f"FS:{word.upper()}" not in result.flat_gloss
    if llm_service.get_repository().get_by_text(word):
        assert word.upper() in result.flat_gloss
        return  # Repository membership takes precedence over demo filtering.
    rule = next(rule for rule in result.grammar_rules if rule.id == "demo_function_word_filter_2")
    assert rule.review_status == "unverified" and "not an ISL" in rule.source


def test_new_filter_still_loses_to_repository_match(tmp_path):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps({"FOR": {"id": "fixture-for", "gloss": "FOR"}}))
    result = llm_service.mock_transform("for", JsonSignRepository(path))
    assert result.flat_gloss == ["FOR"]
    assert "demo_function_word_filter_2" not in {rule.id for rule in result.grammar_rules}


def test_inflections_missing_vocabulary_are_measurable(vocabulary_gaps):
    result = llm_service.mock_transform("bought vegetables nearest")
    assert [(token.gloss, token.fs_reason, token.lemma_tried) for token in result.gloss] == [
        ("FS:BOUGHT", "oov", "buy"),
        ("FS:VEGETABLES", "oov", "vegetable"),
        ("FS:NEAREST", "oov", "near"),
    ]
    assert GlossToken(gloss="FS:HELLO").fs_reason == "explicit"


def test_name_heuristic_and_rest_stream_diagnostics(vocabulary_gaps):
    client = TestClient(app)
    response = client.post("/api/translate", json={"text": "I see Priya"}).json()
    token = next(token for token in response["gloss_detail"] if token["gloss"] == "FS:PRIYA")
    assert token["fs_reason"] == "name_heuristic" and token["lemma_tried"] is None
    item = next(item for item in response["sequence"] if item["gloss"] == "FS:PRIYA")
    assert item["fs_reason"] == "name_heuristic"
    with client.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "bought"})
        meta = ws.receive_json()
        assert meta["gloss_detail"][0]["fs_reason"] == "oov"
        assert ws.receive_json()["item"]["lemma_tried"] == "buy"


def test_synonym_fallback_off_on_and_visible_notice(monkeypatch):
    candidates = Mock(return_value=("water",))  # Mechanical fixture, not semantic equivalence.
    monkeypatch.setattr(english_service, "synonym_candidates", candidates)
    assert llm_service.mock_transform("beverage").flat_gloss == ["FS:BEVERAGE"]
    candidates.assert_not_called()
    monkeypatch.setattr(settings, "ENABLE_SYNONYM_FALLBACK", True)
    result, _, notice = asyncio.run(llm_service.understand("beverage"))
    assert result.flat_gloss == ["WATER"] and result.gloss[0].synonym_from == "beverage"
    assert "meaning may drift" in notice and "not ISL grammar" in notice
    report = build_report(["beverage"])
    assert report["sentences"][0]["gloss_detail"][0]["synonym_from"] == "beverage"
    assert "meaning may drift" in markdown(report)


def test_synonyms_never_applied_to_names_or_filters(monkeypatch):
    candidates = Mock(return_value=("water",))
    monkeypatch.setattr(english_service, "synonym_candidates", candidates)
    monkeypatch.setattr(settings, "ENABLE_SYNONYM_FALLBACK", True)
    for text in ("Priya", "I see Priya", "hello and water", "Beverage"):
        result = llm_service.mock_transform(text)
        assert not any(token.synonym_from for token in result.gloss)
    candidates.assert_not_called()


def test_wordnet_candidates_include_synonyms_and_one_hop_hypernyms(monkeypatch):
    class Lemma:
        def __init__(self, value):
            self.value = value

        def name(self):
            return self.value

    class Synset:
        def __init__(self, words, parents=()):
            self.words, self.parents = words, parents

        def lemmas(self):
            return [Lemma(word) for word in self.words]

        def hypernyms(self):
            return self.parents

    parent = Synset(["fixture_parent"])
    monkeypatch.setattr(
        english_service.wordnet, "synsets", lambda word: [Synset(["fixture_synonym"], [parent])]
    )
    english_service.synonym_candidates.cache_clear()
    try:
        assert english_service.synonym_candidates("fixture-input") == (
            "fixture synonym",
            "fixture parent",
        )
    finally:
        english_service.synonym_candidates.cache_clear()


def test_coverage_json_markdown_and_cli_fixture(tmp_path, vocabulary_gaps):
    fixture = tmp_path / "sentences.txt"
    fixture.write_text("bought vegetables\nbought vegetables\nHello\n\n", encoding="utf-8")
    report = build_report(fixture.read_text().splitlines())
    assert report["sentence_count"] == 3 and report["fs_count"] == 4
    assert report["fs_rate"] == 0.8 and report["error_count"] == 0
    assert report["top_oov_words"] == [
        {"word": "bought", "frequency": 2, "lemma_tried": "buy"},
        {"word": "vegetables", "frequency": 2, "lemma_tried": "vegetable"},
    ]
    assert "80.0%" in markdown(report) and "| bought | 2 | buy |" in markdown(report)
    output, md = tmp_path / "report.json", tmp_path / "report.md"
    assert main([str(fixture), "--json-output", str(output), "--markdown-output", str(md)]) == 0
    assert json.loads(output.read_text())["fs_rate"] == 0.8
    assert md.read_text().startswith("## English vocabulary coverage")


def test_report_excludes_names_from_oov_ranking_and_discloses_failures(tmp_path):
    assert build_report(["Priya"])["top_oov_words"] == []
    report = build_report(["fixture"], transform=Mock(side_effect=RuntimeError("fixture")))
    assert report["error_count"] == 1 and report["fs_rate"] is None
    output, md = tmp_path / "report.json", tmp_path / "report.md"
    assert (
        main(
            [str(tmp_path / "missing"), "--json-output", str(output), "--markdown-output", str(md)]
        )
        == 0
    )
    assert json.loads(output.read_text())["input_error"] == "FileNotFoundError"
    assert "not measurable" in md.read_text()
    assert main([]) == 0


def test_report_never_constructs_sdk_even_in_api_mode(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "api")
    constructor = Mock(side_effect=AssertionError("No SDK use allowed in report"))
    monkeypatch.setattr(llm_service, "AsyncAnthropic", constructor)
    report = build_report(["Hello"])
    assert report["error_count"] == 0 and report["fs_count"] == 0
    assert build_report(["", "   "])["fs_rate"] is None
    constructor.assert_not_called()


def test_domain_input_has_sixty_english_sentences():
    sentences = (Path(__file__).parents[2] / "eval/domain_sentences.txt").read_text().splitlines()
    assert len(sentences) == 60 and all(sentence.strip() for sentence in sentences)
    assert not any("FS:" in sentence or "ISL" in sentence for sentence in sentences)
