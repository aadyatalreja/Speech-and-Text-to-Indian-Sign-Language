"""Synthetic rig fixtures only: values below are NOT ISL linguistic rules."""
import json

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from models.markers import GlossToken, NonManualMarkers
from models.translation import LLMResult
from services import marker_service
from services.llm_service import parse_llm_json
from services.marker_service import apply_markers, load_rules
from services.sequence_service import SignSequenceService


def fixture_rule(**updates):
    return {"id": "synthetic_question", "source": "synthetic test fixture; not ISL",
            "review_status": "unverified", "enabled": True,
            "when": {"intent": "question"}, "span": "sentence", "nmm": {"brow": 0.4}, **updates}


def write_rules(tmp_path, rules):
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "rules": rules}), encoding="utf-8")
    return path


def test_legacy_and_structured_gloss_inputs():
    old = LLMResult(intent="question", gloss=["HELLO", "FS:PRIYA"])
    assert old.flat_gloss == ["HELLO", "FS:PRIYA"]
    assert old.sentence.intent == "question"
    assert [token.fs for token in old.gloss] == [False, True]
    parsed = parse_llm_json(json.dumps({"gloss": [{"gloss": "hello"}, {"gloss": "priya", "fs": True}]}))
    assert parsed.flat_gloss == ["HELLO", "FS:PRIYA"]


def test_bundled_rules_are_disabled_and_empty():
    assert all(not rule.enabled and not rule.nmm.model_dump(exclude_none=True) for rule in load_rules())
    result, notice = apply_markers(LLMResult(gloss=["HELLO"]), "Hello")
    assert result.gloss[0].nmm.model_dump(exclude_none=True) == {}
    assert notice is None


def test_sentence_question_span_and_toggle(tmp_path):
    rule = fixture_rule()
    path = write_rules(tmp_path, [rule])
    original = LLMResult(intent="question", gloss=["YOU", "GO"])
    result, notice = apply_markers(original, "Can you go?", path)
    assert result.sentence.question_type == "yes_no"
    assert all(token.nmm.brow == 0.4 and token.nmm_rules == [rule["id"]] for token in result.gloss)
    assert "not verified ISL" in notice
    assert original.gloss[0].nmm.brow is None
    write_rules(tmp_path, [{**rule, "enabled": False}])
    disabled, notice = apply_markers(result, "Can you go?", path)
    assert all(token.nmm.brow is None and token.nmm_rules == [] for token in disabled.gloss)
    assert notice is None


def test_negation_gloss_span_and_merged_channels(tmp_path):
    path = write_rules(tmp_path, [fixture_rule(), fixture_rule(
        id="synthetic_negation", when={"negated": True}, span="gloss", glosses=["NOT"],
        nmm={"head": [4, 5, 6], "mouth": 0.2})])
    result, notice = apply_markers(LLMResult(intent="question", gloss=["YOU", "GO", "NOT"]), "Will you not go?", path)
    assert result.sentence.negated
    assert result.gloss[0].nmm.head is None
    assert result.gloss[-1].nmm.model_dump() == {"brow": 0.4, "head": (4, 5, 6), "mouth": 0.2}
    sequence, _ = SignSequenceService().build(result.gloss)
    assert sequence[-1].nmm == result.gloss[-1].nmm
    assert sequence[-1].nmm_rules == ["synthetic_question", "synthetic_negation"]
    assert not sequence[-1].nmm_verified and notice


def test_wh_condition_and_unmatched_rule(tmp_path):
    path = write_rules(tmp_path, [fixture_rule(when={"question_type": "wh"})])
    result, _ = apply_markers(LLMResult(intent="question", gloss=["WHERE"]), "Where?", path)
    assert result.sentence.question_type == "wh" and result.gloss[0].nmm.brow == 0.4
    statement, _ = apply_markers(LLMResult(gloss=["GO"]), "Go", path)
    assert statement.gloss[0].nmm.brow is None


def test_verified_and_unverified_rule_provenance(tmp_path):
    path = write_rules(tmp_path, [fixture_rule(review_status="verified", needs_signer_review=False),
        fixture_rule(id="draft_mouth", nmm={"mouth": 0.1}, span="gloss", glosses=["GO"])])
    result, notice = apply_markers(LLMResult(intent="question", gloss=["YOU", "GO"]), "Go?", path)
    assert result.gloss[0].nmm_verified
    assert not result.gloss[1].nmm_verified
    assert "draft_mouth" in notice and "synthetic_question" not in notice


def test_untrusted_model_markers_and_verification_are_discarded(tmp_path):
    path = write_rules(tmp_path, [])
    result, notice = apply_markers(LLMResult(gloss=[{"gloss": "HELLO", "nmm": {"brow": 1},
        "nmm_rules": ["invented"], "nmm_verified": True}]), "Hello", path)
    assert result.gloss[0].nmm.brow is None
    assert result.gloss[0].nmm_rules == [] and not result.gloss[0].nmm_verified
    assert notice is None


@pytest.mark.parametrize("values", [{"brow": 2}, {"mouth": -1}, {"head": [0, 0]},
                                      {"head": [0, 91, 0]}, {"brow": float("nan")}, {"invented": 1}])
def test_nmm_validation(values):
    with pytest.raises(ValidationError):
        NonManualMarkers(**values)


@pytest.mark.parametrize("updates", [{"source": ""}, {"review_status": "approved"},
    {"nmm": {}}, {"when": {"imagined": True}}, {"span": "gloss"}])
def test_invalid_config_fails_explicitly(tmp_path, updates):
    with pytest.raises(ValidationError):
        load_rules(write_rules(tmp_path, [fixture_rule(**updates)]))


def test_rest_and_stream_keep_flat_compatibility_and_marker_details(monkeypatch, tmp_path):
    grammar = [rule.model_dump() for rule in marker_service.load_config().grammar]
    path = write_rules(tmp_path, [fixture_rule()])
    data = yaml.safe_load(path.read_text())
    data["grammar"] = grammar
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(marker_service, "RULES_PATH", path)
    client = TestClient(app)
    body = client.post("/api/translate", json={"text": "Can you help me?"}).json()
    assert body["gloss"] == ["YOU", "HELP", "ME"]
    assert [item["gloss"] for item in body["gloss_detail"]] == body["gloss"]
    assert body["sentence"] == {"intent": "question", "question_type": "yes_no", "negated": False, "topic": None}
    assert all(item["nmm"]["brow"] == 0.4 for item in body["sequence"])
    with client.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "Can you help me?"})
        meta = ws.receive_json()
        assert meta["gloss_detail"] == body["gloss_detail"] and meta["sentence"] == body["sentence"]
        for item in body["sequence"]:
            assert ws.receive_json()["item"] == item
        assert ws.receive_json()["type"] == "done"
