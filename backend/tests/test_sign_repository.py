from services.sign_repository import JsonSignRepository

def test_repo():
    r = JsonSignRepository()
    assert r.get_sign("hello").id == "hello"
    assert r.get_sign("NOPE") is None
    assert any(s.gloss == "WATER" for s in r.search("wat"))
    assert [g for g, s in r.get_sequence(["I", "ZZZ"]) if s is None] == ["ZZZ"]
