"""Expose playback files and public provenance, never private registry metadata."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings
from services.sign_repository import get_repository, ReloadingFile

router = APIRouter()
PUBLIC_FIELDS = {"source", "licence", "signer", "review_status", "duration", "clip"}


_alphabet_file = ReloadingFile()


def alphabet_manifest():
    path = settings.SIGN_DATA_PATH / "alphabet" / "manifest.json"

    def load(path):
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("version") != 1
            or not isinstance(value.get("characters"), dict)
            or any(not isinstance(entry, dict) for entry in value["characters"].values())
        ):
            raise ValueError("Invalid alphabet manifest")
        return value

    try:
        return _alphabet_file.get(path, load)
    except FileNotFoundError:
        return {"version": 1, "characters": {}}


@router.get("/api/alphabet")
def alphabet():
    manifest = alphabet_manifest()
    return {
        "version": manifest["version"],
        "characters": {
            character: {key: value for key, value in entry.items() if key in PUBLIC_FIELDS}
            for character, entry in manifest["characters"].items()
            if entry.get("review_decision") != "rejected"
        },
    }


@router.get("/api/avatar-clips")
def avatar_clips():
    return [
        {"gloss": sign.gloss, "clip_url": f"/signs/{sign.clip}"}
        for sign in sorted(get_repository().search(""), key=lambda sign: sign.gloss)
        if sign.clip
        and sign.review_decision != "rejected"
        and sign.clip_review_decision != "rejected"
    ]


@router.get("/signs/{relative:path}")
def sign_asset(relative: str):
    root = settings.SIGN_DATA_PATH.resolve()
    try:
        path = (root / relative).resolve()
    except (OSError, ValueError):
        raise HTTPException(404, "Not found")
    if not path.is_relative_to(root) or path.name in {"signs.json", "manifest.json"}:
        raise HTTPException(404, "Not found")
    allowed = set()
    clips = set()
    for sign in get_repository().search(""):
        if sign.review_decision == "rejected":
            continue
        if sign.video:
            allowed.add((root / sign.video).resolve())
        if sign.clip and sign.clip_review_decision != "rejected":
            clips.add((root / sign.clip).resolve())
    for entry in alphabet_manifest()["characters"].values():
        if entry.get("clip") and entry.get("review_decision") != "rejected":
            clips.add((root / "alphabet" / Path(entry["clip"])).resolve())
    allowed.update(clips)
    if path not in allowed or not path.is_file():
        raise HTTPException(404, "Not found")
    if path in clips:
        clip = json.loads(path.read_text(encoding="utf-8"))
        if clip.get("review_decision") == "rejected":
            raise HTTPException(404, "Not found")
        # Offline clip review also writes private audit fields into clip JSON.
        return {
            key: value
            for key, value in clip.items()
            if key not in {"reviewer", "review_history", "evidence"}
            and not key.startswith("import_")
        }
    return FileResponse(path)
