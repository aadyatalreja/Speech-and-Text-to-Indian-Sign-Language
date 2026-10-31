from services.sign_repository import JsonSignRepository

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
