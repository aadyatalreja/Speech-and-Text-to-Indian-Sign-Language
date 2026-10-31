import copy
import json
import string

import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app
from tools.validate_signs import validate_alphabet, validate_signs


def missing_manifest():
    return {"version": 1, "characters": {char: {
        "clip": None, "source": None, "licence": None, "signer": None,
        "review_status": "unverified", "duration": None, "notes": "TODO: real asset and signer review"}
        for char in string.ascii_uppercase + string.digits}}


def fixture_manifest(tmp_path):
    root = tmp_path / "alphabet"
    root.mkdir()
    data = missing_manifest()
    data["characters"]["A"].update(clip="a.json", source="synthetic software fixture",
        licence="test only; no real ISL recording", signer="synthetic", duration=1, review_status="unverified")
    clip = {"version": 1, "id": "fixture", "gloss": "A", "kind": "dataset", "keys": [
        {"t": 0, "R": {"p": [0, 0, 0]}, "L": {"p": [1, 0, 0]}},
        {"t": 1, "R": {"p": [0, 1, 0]}, "L": {"p": [1, 1, 0]}}]}
    (root / "a.json").write_text(json.dumps(clip), encoding="utf-8")
    path = root / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data, clip


def test_bundled_missing_characters_are_explicit_and_served():
    path = settings.SIGN_DATA_PATH / "alphabet" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data["characters"]) == set(string.ascii_uppercase + string.digits)
    assert all(entry["clip"] is None and entry["review_status"] == "unverified" and "TODO" in entry["notes"]
               for entry in data["characters"].values())
    assert validate_alphabet(path) == []
    assert TestClient(app).get("/signs/alphabet/manifest.json").json() == data


def test_valid_two_hand_fixture_and_sign_validator_integration(tmp_path):
    path, _, _ = fixture_manifest(tmp_path)
    assert validate_alphabet(path) == []
    database = tmp_path / "signs.json"
    database.write_text("{}")
    assert validate_signs(database) == []
    (path.parent / "a.json").unlink()
    assert any("Alphabet A" in error for error in validate_signs(database))


@pytest.mark.parametrize("field,value", [("source", None), ("licence", ""), ("signer", " "),
    ("duration", None), ("duration", -1), ("clip", "../outside.json"),
    ("review_status", "approved")])
def test_manifest_rejects_invalid_asset_metadata(tmp_path, field, value):
    path, data, _ = fixture_manifest(tmp_path)
    data["characters"]["A"][field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    assert validate_alphabet(path)


def test_missing_clip_cannot_claim_verification(tmp_path):
    path, data, _ = fixture_manifest(tmp_path)
    data["characters"]["B"]["review_status"] = "verified"
    path.write_text(json.dumps(data))
    assert validate_alphabet(path)


@pytest.mark.parametrize("mutation", ["gloss", "time", "hands", "shape", "quaternion"])
def test_invalid_clip_data_is_rejected(tmp_path, mutation):
    path, _, original = fixture_manifest(tmp_path)
    clip = copy.deepcopy(original)
    if mutation == "gloss":
        clip["gloss"] = "B"
    elif mutation == "time":
        clip["keys"][0]["t"] = -1
    elif mutation == "hands":
        clip["keys"] = [{"t": 0}]
    elif mutation == "shape":
        clip["keys"][0]["R"]["shape"] = [5] * 5
    else:
        clip["keys"][0]["R"]["q"] = [0] * 4
    (path.parent / "a.json").write_text(json.dumps(clip))
    assert validate_alphabet(path)
