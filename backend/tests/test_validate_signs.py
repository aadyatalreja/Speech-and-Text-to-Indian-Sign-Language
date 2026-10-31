import json
import subprocess
import sys
from pathlib import Path

import pytest

from config import settings
from tools.validate_signs import validate_signs


def write_db(tmp_path, entries):
    path = tmp_path / "signs.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_bundled_database_is_valid():
    assert validate_signs(settings.SIGN_DATA_PATH / "signs.json") == []


def test_legacy_demo_is_valid(tmp_path):
    assert validate_signs(write_db(tmp_path, {"HELLO": {"id": "hello", "gloss": "HELLO"}})) == []


@pytest.mark.parametrize("field", ["video", "clip", "keypoints"])
def test_missing_references(tmp_path, field):
    errors = validate_signs(write_db(tmp_path, {"HELLO": {"id": "hello", "gloss": "HELLO", field: "missing"}}))
    assert any(f"missing {field} file" in error for error in errors)


def test_non_demo_provenance_and_existing_files(tmp_path):
    entry = {"id": "hello", "gloss": "HELLO", "asset_type": "video", "video": "hello.mp4"}
    path = write_db(tmp_path, {"HELLO": entry})
    errors = validate_signs(path)
    for field in ("source", "licence", "signer", "review_status"):
        assert any(field in error for error in errors)
    (tmp_path / "hello.mp4").write_bytes(b"fixture, not a real sign")
    entry.update(source="synthetic test", licence="test only", signer="synthetic", review_status="unverified")
    assert validate_signs(write_db(tmp_path, {"HELLO": entry})) == []


@pytest.mark.parametrize("extra, fragment", [
    ({"id": "HELLO"}, "duplicate id"),
    ({"aliases": ["hello"]}, "duplicate alias/lookup"),
    ({"aliases": ["thank_you", " Thank  You "]}, "duplicate alias"),
    ({"clip": "../escape.json"}, "relative file"),
    ({"review_status": "approved"}, "invalid sign schema"),
    ({"asset_type": "invented"}, "invalid sign schema"),
])
def test_invalid_entries(tmp_path, extra, fragment):
    entries = {"HELLO": {"id": "hello", "gloss": "HELLO"},
               "OTHER": {"id": "other", "gloss": "OTHER", **extra}}
    assert any(fragment in error for error in validate_signs(write_db(tmp_path, entries)))


def test_cli_fails_on_invalid_json(tmp_path):
    path = tmp_path / "signs.json"
    path.write_text('{"HELLO": {}, "HELLO": {}}', encoding="utf-8")
    tool = Path(__file__).resolve().parents[1] / "tools" / "validate_signs.py"
    result = subprocess.run([sys.executable, str(tool), str(path)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Duplicate JSON key" in result.stderr
