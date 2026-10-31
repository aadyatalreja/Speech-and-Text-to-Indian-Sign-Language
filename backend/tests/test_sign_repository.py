from services.sign_repository import JsonSignRepository
import json
import pytest


def test_legacy_defaults_and_lookup(tmp_path):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps({"THANK_YOU": {"id": "thanks", "gloss": "THANK_YOU",
        "aliases": ["much obliged"], "lemma": "thank", "category": "Social"},
        "HELLO": {"id": "hello", "gloss": "HELLO"}}))
    repo = JsonSignRepository(path)
    for text in [" thank__you ", "THANK YOU", " Much   Obliged ", "thank"]:
        assert repo.get_by_text(text).id == "thanks"
    assert repo.get_by_text("missing") is None
    assert [s.id for s in repo.search("oblig")] == ["thanks"]
    assert repo.list_glosses() == ["THANK_YOU", "HELLO"]
    assert [s.id for s in repo.list_by_category(" social ")] == ["thanks"]
    assert repo.list_by_category("missing") == []
    old = repo.get_sign("hello")
    assert old.aliases == [] and old.review_status == "unverified"
    assert old.source is None and old.licence is None and old.signer is None


def test_repository_rejects_ambiguous_alias(tmp_path):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps({"HELLO": {"id": "hello", "gloss": "HELLO"},
        "OTHER": {"id": "other", "gloss": "OTHER", "aliases": ["Hello"]}}))
    with pytest.raises(ValueError, match="Ambiguous sign alias"):
        JsonSignRepository(path)


def test_repository_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps({"HELLO": {"id": "hello", "gloss": "HELLO"},
        "OTHER": {"id": "HELLO", "gloss": "OTHER"}}))
    with pytest.raises(ValueError, match="Duplicate sign id"):
        JsonSignRepository(path)

def test_repo():
    r = JsonSignRepository()
    assert r.get_sign("hello").id == "hello"
    assert r.get_sign("NOPE") is None
    assert any(s.gloss == "WATER" for s in r.search("wat"))
    assert [g for g, s in r.get_sequence(["I", "ZZZ"]) if s is None] == ["ZZZ"]

def test_clip_url_reaches_the_sequence(tmp_path):
    import json
    from services.sequence_service import SignSequenceService
    f = tmp_path / "signs.json"
    f.write_text(json.dumps({"HELLO": {"id": "hello", "gloss": "HELLO", "asset_type": "dataset", "clip": "clips/hello.json"},
                             "YOU": {"id": "you", "gloss": "YOU"}}))
    items, unknown = SignSequenceService(JsonSignRepository(f)).build(["HELLO", "YOU", "ZZZ"])
    assert items[0].clip_url == "/signs/clips/hello.json"
    assert items[1].clip_url is None and items[2].clip_url is None
    assert unknown == ["ZZZ"]
