"""Export human-review JSON and apply explicit decisions locally; no HTTP writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BASE, settings
from models.alphabet import AlphabetManifest
from services.marker_service import MarkerConfig
from tools.bulk_import import read_json, atomic_json, file_hash, local_target, registry_lock
from tools.validate_signs import validate_signs


class ReviewForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    kind: Literal["sign", "clip", "rule", "alphabet"]
    id: str = Field(min_length=1)
    document_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    asset_hashes: dict[str, str]
    snapshot: dict
    decision: Literal["verified", "rejected"]
    reviewer: str = Field(min_length=1)
    comments: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


def locate(kind, identifier, root, grammar):
    if kind == "rule":
        path = Path(grammar)
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        matches = [rule for section in ("rules", "grammar") for rule in document.get(section, []) if rule["id"] == identifier]
        if len(matches) != 1: raise ValueError("Rule ID must identify exactly one rule")
        return path, document, matches[0]
    if kind == "clip":
        if not identifier.startswith("clips/") or not identifier.endswith(".json"):
            raise ValueError("Clip ID must be clips/<relative>.json")
        path = local_target(root, identifier)
        if not path.is_relative_to((root / "clips").resolve()):
            raise ValueError("Clip review must stay inside clips/")
        document = read_json(path)
        return path, document, document
    path = local_target(root, "signs.json" if kind == "sign" else "alphabet/manifest.json")
    document = read_json(path)
    record = document.get(identifier) if kind == "sign" else document.get("characters", {}).get(identifier)
    if not isinstance(record, dict): raise ValueError("Review target not found")
    return path, document, record


def hashes(kind, record, root):
    if kind not in {"sign", "alphabet"}: return {}
    result = {}
    for field in ("clip", "video", "keypoints"):
        if reference := record.get(field):
            relative = f"alphabet/{reference}" if kind == "alphabet" else reference
            result[relative] = file_hash(local_target(root, relative))
    return result


def export_review(kind, identifier, root=None, grammar=None):
    root = Path(root or settings.SIGN_DATA_PATH).resolve()
    grammar = Path(grammar or BASE / "data/grammar/isl_rules.yaml").resolve()
    path, _, record = locate(kind, identifier, root, grammar)
    return {"version": 1, "kind": kind, "id": identifier, "document_sha256": file_hash(path),
        "asset_hashes": hashes(kind, record, root), "snapshot": record,
        "decision": None, "reviewer": "", "comments": "", "evidence": ""}


def write_document(path, document, yaml_file=False):
    if not yaml_file:
        atomic_json(path, document)
        return
    # Atomic replace also works for YAML; serialization is kept human-editable.
    import os, tempfile
    handle, temporary = tempfile.mkstemp(prefix=".review-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            yaml.safe_dump(document, stream, sort_keys=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_review(payload, root=None, grammar=None):
    form = ReviewForm.model_validate(payload)
    if not all(value.strip() for value in (form.reviewer, form.comments, form.evidence)):
        raise ValueError("Reviewer, comments, and evidence must not be blank")
    root = Path(root or settings.SIGN_DATA_PATH).resolve()
    grammar = Path(grammar or BASE / "data/grammar/isl_rules.yaml").resolve()
    with registry_lock(root):
        path, document, record = locate(form.kind, form.id, root, grammar)
        if file_hash(path) != form.document_sha256 or record != form.snapshot or hashes(form.kind, record, root) != form.asset_hashes:
            raise ValueError("Stale review: target or referenced assets changed; export again")
        verified = form.decision == "verified"
        if verified and form.kind in {"sign", "clip", "alphabet"}:
            if not all((record.get(field) or "").strip() for field in ("source", "licence", "signer")):
                raise ValueError("Verification requires source, licence, and signer metadata")
            if form.kind == "sign" and (record.get("asset_type", "demo") == "demo" or not (record.get("clip") or record.get("video"))):
                raise ValueError("Cannot verify a demo/missing sign asset")
            if form.kind == "alphabet" and not record.get("clip"):
                raise ValueError("Cannot verify a missing alphabet asset")
            if form.kind == "clip" and (record.get("kind") != "dataset" or record.get("version") != 1 or not record.get("keys")):
                raise ValueError("Cannot verify a demo/invalid clip")
            if form.kind == "sign" and record.get("clip"):
                clip = read_json(local_target(root, record["clip"]))
                if clip.get("review_decision") == "rejected":
                    raise ValueError("Referenced clip is rejected; review/correct the clip first")
        if verified and form.kind == "rule":
            if record.get("operation") == "pending" or ("nmm" in record and not any(value is not None for value in record["nmm"].values())):
                raise ValueError("Cannot verify an unconfigured rule placeholder")
            if not (record.get("source") or "").strip() or record["source"].startswith("TODO"):
                raise ValueError("Rule verification needs a real source reference")
        event = {"decision": form.decision, "reviewer": form.reviewer, "comments": form.comments,
            "evidence": form.evidence, "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "document_sha256": form.document_sha256, "asset_hashes": form.asset_hashes}
        record["review_status"] = "verified" if verified else "unverified"
        record["review_decision"] = form.decision
        record["reviewer"] = form.reviewer
        record.setdefault("review_history", []).append(event)
        if form.kind == "sign":
            record["needs_manual_review"] = not verified
            if verified: record["clip_review_decision"] = None
        if form.kind == "rule":
            if "needs_signer_review" in record: record["needs_signer_review"] = not verified
            if not verified: record["enabled"] = False
            MarkerConfig.model_validate(document)
        if form.kind == "alphabet": AlphabetManifest.model_validate(document)
        # Validate a sign candidate without changing the original registry.
        if form.kind == "sign":
            import tempfile
            with tempfile.NamedTemporaryFile(prefix=".review-", suffix=".json", dir=root, delete=False) as temp:
                candidate = Path(temp.name)
            try:
                atomic_json(candidate, document)
                if errors := validate_signs(candidate): raise ValueError("Invalid review candidate: " + "; ".join(errors))
            finally: candidate.unlink(missing_ok=True)
        if file_hash(path) != form.document_sha256:
            raise ValueError("Target changed during review application")
        write_document(path, document, form.kind == "rule")
        # Rejected clips also demote their registry references. Clip verification
        # alone never promotes a sign entry without its own asset-hash review.
        if form.kind == "clip" and not verified and (root / "signs.json").is_file():
            signs = read_json(root / "signs.json")
            for sign in signs.values():
                if sign.get("clip") == form.id:
                    sign.update(review_status="unverified", review_decision=None, clip_review_decision="rejected", needs_manual_review=True)
                    sign.setdefault("review_history", []).append({**event, "target_clip": form.id})
            atomic_json(root / "signs.json", signs)
        return event


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "apply"])
    parser.add_argument("file", type=Path, help="review JSON output/input")
    parser.add_argument("--kind", choices=["sign", "clip", "rule", "alphabet"])
    parser.add_argument("--id")
    parser.add_argument("--root", type=Path, default=settings.SIGN_DATA_PATH)
    parser.add_argument("--grammar", type=Path, default=BASE / "data/grammar/isl_rules.yaml")
    args = parser.parse_args(argv)
    try:
        if args.action == "export":
            if not args.kind or not args.id: raise ValueError("Export needs --kind and --id")
            if args.file.exists(): raise ValueError("Export destination exists; choose a new file")
            atomic_json(args.file, export_review(args.kind, args.id, args.root, args.grammar))
        else:
            apply_review(read_json(args.file), args.root, args.grammar)
        print("Review JSON exported; no decision applied." if args.action == "export" else "Explicit human review decision applied; restart backend and reload browser.")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())
