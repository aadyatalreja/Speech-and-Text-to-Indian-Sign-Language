"""Synthetic behavior tests; no fixture asserts real ISL grammar correctness."""
import asyncio
import json

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from models.grammar import GrammarRule
from models.translation import LLMResult
from services import grammar_service, llm_service, marker_service
from services.grammar_service import active_rules, apply_grammar, grammar_notice, verified_examples
from services.sign_repository import get_repository


def rule(**updates):
    return {"id": "synthetic_order", "source": "Synthetic software fixture, not ISL",
            "review_status": "unverified", "enabled": True,
            "operation": "order_categories", "categories": ["time", "rest", "verb"], **updates}


def config(tmp_path, rules):
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "grammar": rules}), encoding="utf-8")
    return path


def examples(tmp_path, rows):
    path = tmp_path / "examples.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def example(**updates):
    return {"english": "Synthetic software fixture only", "gloss": ["HELLO"], "nmm": {},
            "reviewer": "Synthetic fixture reviewer (not a signer)", "review_status": "verified", **updates}


def test_default_draft_grammar_notice_and_per_rule_verification(monkeypatch, tmp_path):
    rules = [rule(id="draft_drop", operation="drop_words", words=["to"]), rule()]
    path = config(tmp_path, rules)
    monkeypatch.setattr(marker_service, "RULES_PATH", path)
    result = llm_service.mock_transform("I go to college tomorrow")
    assert result.flat_gloss == ["TOMORROW", "I", "COLLEGE", "GO"]
    assert {r.id for r in result.grammar_rules} == {"draft_drop", "synthetic_order"}
    assert "Unverified grammar" in grammar_notice(result.grammar_rules)
    rules[1].update(review_status="verified", reviewer="Synthetic test reviewer")
    config(tmp_path, rules)
    notice = grammar_notice(llm_service.mock_transform("I go to college tomorrow").grammar_rules)
    assert "draft_drop" in notice and "synthetic_order" not in notice
    rules[0].update(enabled=False)
    config(tmp_path, rules)
    changed = llm_service.mock_transform("I go to college tomorrow")
    assert "FS:TO" in changed.flat_gloss
    assert grammar_notice(changed.grammar_rules) is None


def test_empty_config_preserves_input_order_and_reports_unknowns(monkeypatch, tmp_path):
    monkeypatch.setattr(marker_service, "RULES_PATH", config(tmp_path, []))
    assert llm_service.mock_transform("I go to college tomorrow").flat_gloss == ["I", "GO", "FS:TO", "COLLEGE", "TOMORROW"]


@pytest.mark.parametrize("operation, args, expected", [
    ("move_category", {"category": "question", "position": "end"}, ["GO", "NOT", "WHERE"]),
    ("move_category", {"category": "negation", "position": "start"}, ["NOT", "WHERE", "GO"]),
    ("repeat", {"category": "verb", "count": 2}, ["WHERE", "GO", "GO", "NOT"]),
    ("topic_first", {}, ["GO", "WHERE", "NOT"]),
])
def test_configured_operators(operation, args, expected):
    r = GrammarRule(**rule(operation=operation, **args))
    result = apply_grammar(LLMResult(gloss=["WHERE", "GO", "NOT"], sentence={"topic": "GO"}),
                           "synthetic fixture", get_repository(), [r])
    assert result.flat_gloss == expected
    assert result.grammar_rules[0].id == r.id


def test_pronoun_indices_are_explicit_labels_not_generated_spatial_poses():
    r = GrammarRule(**rule(operation="pronoun_index", references={"YOU": "fixture_referent"}))
    result = apply_grammar(LLMResult(gloss=["YOU", "GO"]), "fixture", get_repository(), [r])
    assert result.gloss[0].reference == "fixture_referent"
    assert result.gloss[1].reference is None
    assert result.gloss[0].nmm.head is None


def test_disabled_rules_are_not_active(tmp_path):
    assert active_rules(config(tmp_path, [rule(enabled=False)])) == []


def test_repetition_requires_configured_english_trigger():
    r = GrammarRule(**rule(operation="repeat", category="verb", count=2, when_words=["synthetic"]))
    source = LLMResult(gloss=["GO"])
    assert apply_grammar(source, "unmatched", get_repository(), [r]).flat_gloss == ["GO"]
    assert apply_grammar(source, "Synthetic fixture", get_repository(), [r]).flat_gloss == ["GO", "GO"]
    assert source.flat_gloss == ["GO"]


def test_duplicate_grammar_rule_ids_are_rejected(tmp_path):
    with pytest.raises(ValidationError, match="Duplicate"):
        active_rules(config(tmp_path, [rule(), rule()]))


@pytest.mark.parametrize("updates", [
    {"review_status": "verified", "reviewer": None}, {"operation": "pending"},
    {"operation": "move_category"}, {"operation": "pronoun_index"},
    {"categories": ["verb", "verb", "rest"]}, {"source": " "},
])
def test_invalid_rules_are_rejected(updates):
    with pytest.raises(ValidationError):
        GrammarRule(**rule(**updates))


def test_examples_filter_review_status_and_vocabulary(tmp_path):
    rows = [example(), example(english="Draft fixture", review_status="unverified"),
            example(english="Unavailable fixture", gloss=["NOT_IN_VOCAB"]),
            example(english="Explicit spelling fixture", gloss=["FS:PRIYA"])]
    selected = verified_examples(["HELLO"], examples(tmp_path, rows))
    assert [row.english for row in selected] == [rows[0]["english"], rows[3]["english"]]
    assert len(verified_examples(["HELLO"], examples(tmp_path, [example()] * 55))) == 50


def test_empty_examples_do_not_fabricate_content(tmp_path):
    assert verified_examples(["HELLO"], examples(tmp_path, [])) == []


def test_verified_examples_require_reviewer(tmp_path):
    with pytest.raises(ValueError, match="reviewer"):
        verified_examples(["HELLO"], examples(tmp_path, [example(reviewer=None)]))


def test_mocked_prompt_uses_same_config_and_verified_examples(monkeypatch, tmp_path):
    monkeypatch.setattr(marker_service, "RULES_PATH", config(tmp_path, [rule()]))
    monkeypatch.setattr(grammar_service, "EXAMPLES_PATH", examples(tmp_path, [example(),
        example(english="DO_NOT_INCLUDE_DRAFT", review_status="unverified")]))
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "fake-test-key")
    seen = []
    def handler(request):
        seen.append(json.loads(request.content)["system"])
        return httpx.Response(200, json={"content": [{"text": json.dumps({"gloss": ["HELLO"],
            "grammar_rules": [{"id": "forged", "source": "fake", "review_status": "verified"}]})}]})
    client = httpx.AsyncClient
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", lambda **kwargs: client(
        transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(llm_service.api_transform("Hello"))
    assert '"id": "synthetic_order"' in seen[0]
    assert '"review_status": "unverified"' in seen[0]
    assert "Synthetic software fixture only" in seen[0] and "DO_NOT_INCLUDE_DRAFT" not in seen[0]
    assert "forged" not in {r.id for r in result.grammar_rules}
    assert "Unverified grammar" in grammar_notice(result.grammar_rules)


def test_rest_and_stream_expose_grammar_notice_and_rule_status():
    client = TestClient(app)
    response = client.post("/api/translate", json={"text": "I need help"}).json()
    assert "Unverified grammar" in response["notice"]
    assert response["grammar_rules"] and all(r["review_status"] == "unverified" for r in response["grammar_rules"])
    with client.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "I need help"})
        meta = ws.receive_json()
        assert meta["notice"] == response["notice"] and meta["grammar_rules"] == response["grammar_rules"]
        for _ in response["sequence"]:
            ws.receive_json()
        assert ws.receive_json()["type"] == "done"
