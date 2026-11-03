"""Hash-bound sentence review packets. No generated judgement or asset promotion."""

import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_COLUMNS = [
    "item_id",
    "stimulus_sha256",
    "gloss_acceptable",
    "nmm_correct",
    "comprehension",
    "comments",
    "reviewed_gloss",
    "acceptable_alternatives",
    "expected_nmm",
    "signer_dialect",
    "decision",
    "signed_off",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_paths():
    """Bind configuration, lexical data, actual clip assets and rendering code."""
    paths = [ROOT / "eval/isl_testset.jsonl", ROOT / "frontend/package-lock.json"]
    for directory in (
        "backend/data/signs",
        "backend/data/grammar",
        "backend/data/lexicon",
        "backend/services",
        "backend/models",
        "frontend/src/avatar",
    ):
        paths.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".json", ".yaml", ".mp4", ".webm"}
        )
    paths += [
        ROOT / "backend/config.py",
        ROOT / "paper/render_avatar.ts",
        ROOT / "paper/render_avatar.mjs",
    ]
    paths.extend((ROOT / "eval").glob("*.py"))
    paths.extend((ROOT / "eval/tools").glob("*.py"))
    paths.extend((ROOT / "paper").glob("*.py"))
    paths += [ROOT / "backend/requirements.txt", ROOT / "paper/requirements.txt"]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(set(paths)) if p.exists()}


async def create_packet(sentences, directory, source_language="English", translator=None):
    from services.gloss_service import translate
    from models.translation import TranslationRequest
    from config import settings

    directory = Path(directory)
    if directory.exists():
        raise ValueError("Refusing to overwrite an existing reviewer packet")
    items = []
    for index, sentence in enumerate(sentences):
        response = await (translator or translate)(
            TranslationRequest(text=sentence, source_language=source_language)
        )
        stimulus = {
            "source_text": sentence,
            "source_language": source_language,
            "translation": response.model_dump(mode="json"),
        }
        items.append(
            {
                "item_id": f"item-{index + 1:03d}",
                "stimulus": stimulus,
                "stimulus_sha256": digest(stimulus),
                "frame_strip": f"frames/item-{index + 1:03d}.svg",
            }
        )
    manifest = {
        "version": 1,
        "disclaimer": "Engineering stimuli only; all demo assets, expressions and interpolation remain NOT verified ISL. No judgements are prefilled.",
        "configuration": {
            k: getattr(settings, k)
            for k in (
                "LLM_PROVIDER",
                "LLM_ORDERING",
                "ENABLE_SYNONYM_FALLBACK",
                "ENABLE_DEMO_INDIC_GLOSSARY",
                "LLM_MODEL",
            )
        },
        "source_hashes": snapshot_paths(),
        "items": items,
    }
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (directory / "responses.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {"item_id": item["item_id"], "stimulus_sha256": item["stimulus_sha256"]}
            for item in items
        )
    return manifest


def write_packet_html(directory, compact=False):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    sections = []
    for item in manifest["items"]:
        stimulus = item["stimulus"]
        frame = directory / item["frame_strip"]
        if not frame.is_file():
            raise ValueError("Missing rendered frame strip; packet is incomplete")
        if compact and frame.suffix == ".svg":
            from paper.svg_raster import rasterize

            png = frame.with_suffix(".png")
            blinded = frame.with_name(frame.stem + "-blinded.png")
            rasterize(frame, png)
            rasterize(frame, blinded, hide_text=True)
            item["frame_strip"] = png.relative_to(directory).as_posix()
            item["blinded_strip"] = blinded.relative_to(directory).as_posix()
            if not frame.resolve().is_relative_to(directory.resolve()):
                raise ValueError("Frame escapes packet")
            frame.unlink()  # Fresh generated projection only; never a human form.
        sections.append(
            f'<section><h2>{html.escape(item["item_id"])}</h2><p>Source: {html.escape(stimulus["source_text"])}</p><p>English intermediate: {html.escape(stimulus["translation"].get("english_text") or "")}</p><p>Gloss: {html.escape(" ".join(stimulus["translation"]["gloss"]))}</p><img alt="Frame strip of the actual demo sequence; review motion separately" src="{item["frame_strip"]}"/><p>{html.escape(stimulus["translation"].get("notice") or "")}</p><p>Record in responses.csv: acceptable gloss (yes/no/uncertain), correct NMM (yes/no/uncertain), comprehension (1–5), comments; optional corrected reference gloss and aligned numeric NMM JSON.</p></section>'
        )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Signer review packet — unverified demo</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;color:#172b3a}section{break-inside:avoid;border-top:1px solid #aaa;padding:1rem 0}img{width:100%}strong{color:#923000}</style><h1>Signer/linguist review packet</h1><strong>NOT verified ISL. Frame strips do not demonstrate motion timing or comprehension.</strong><p>No judgements are prefilled. Review complete motion in the app/linked source assets before judging temporal NMM. Use a private consented reviewer pseudonym; do not add names to this sheet.</p>'
        + "".join(sections)
        + "</html>"
    )
    (directory / "review.html").write_text(page, encoding="utf-8")
    manifest["render_hashes"] = {
        name: file_hash(directory / name)
        for name in [
            "review.html",
            *[item["frame_strip"] for item in manifest["items"]],
            *[item["blinded_strip"] for item in manifest["items"] if "blinded_strip" in item],
        ]
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (directory / "manifest.sha256").write_text(
        file_hash(directory / "manifest.json") + "\n", encoding="ascii"
    )


def validate_packet(directory):
    from config import settings

    directory = Path(directory)
    if (
        file_hash(directory / "manifest.json")
        != (directory / "manifest.sha256").read_text().strip()
    ):
        raise ValueError("Stale/tampered packet manifest; export again")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if any(getattr(settings, name) != value for name, value in manifest["configuration"].items()):
        raise ValueError(
            "Stale export: configuration changed; restore the frozen configuration or export again"
        )
    for relative, expected in manifest["source_hashes"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or file_hash(path) != expected:
            raise ValueError(
                "Stale export: pipeline, target, or referenced asset changed; export again"
            )
    for relative, expected in manifest["render_hashes"].items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory.resolve()) or file_hash(path) != expected:
            raise ValueError("Stale rendered stimulus; export again")
    if any(digest(item["stimulus"]) != item["stimulus_sha256"] for item in manifest["items"]):
        raise ValueError("Stimulus hash mismatch")
    return manifest


def import_packet(directory, sheet, output, reviewer="", reviewer_id="", evidence=""):
    from eval.run_eval import EvalRow
    from eval.metrics import Judgement
    from models.markers import NonManualMarkers
    from tools.bulk_import import atomic_json, registry_lock

    directory, output = Path(directory), Path(output)
    reviewer, reviewer_id, evidence = reviewer.strip(), reviewer_id.strip(), evidence.strip()
    # Serialize all validation/read/replace operations. No sign/rule status is altered.
    with registry_lock(output.parent):
        manifest = validate_packet(directory)
        items = {item["item_id"]: item for item in manifest["items"]}
        existing = (
            [
                EvalRow.model_validate(json.loads(line))
                for line in output.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if output.exists()
            else []
        )
        original_hash = file_hash(output) if output.exists() else None
        receipt_path = output.with_suffix(".import-receipt.json")
        if output.exists():
            if (
                not receipt_path.exists()
                or json.loads(receipt_path.read_text())["output_sha256"] != original_hash
            ):
                raise ValueError(
                    "Stale or unbound import target; preserve/adjudicate it and export again"
                )
            if json.loads(receipt_path.read_text())["manifest_sha256"] != file_hash(
                directory / "manifest.json"
            ):
                raise ValueError("Import target belongs to a different packet; use a fresh target")
        seen = set()
        with Path(sheet).open(encoding="utf-8-sig", newline="") as stream:
            responses = list(csv.DictReader(stream))
        for response in responses:
            ident = response["item_id"]
            if ident in seen or ident not in items:
                raise ValueError("Duplicate or unknown item in review sheet")
            seen.add(ident)
            item = items[ident]
            if response["stimulus_sha256"] != item["stimulus_sha256"]:
                raise ValueError("Stale response stimulus hash")
            if not any(
                response.get(k, "").strip()
                for k in (
                    "gloss_acceptable",
                    "nmm_correct",
                    "comprehension",
                    "comments",
                    "reviewed_gloss",
                    "decision",
                    "signed_off",
                )
            ):
                continue  # A blank form is not a judgement.
            signed = response.get("signed_off", "").strip().lower()
            decision = response.get("decision", "").strip()
            if signed not in {"", "yes", "no"} or decision not in {
                "",
                "in_review",
                "verified",
                "rejected",
            }:
                raise ValueError("Invalid explicit decision/sign-off")
            if not reviewer_id.strip():
                raise ValueError("A consented reviewer pseudonym is required")
            if (signed == "yes" or decision == "verified") and not all(
                v.strip() for v in (reviewer, evidence)
            ):
                raise ValueError("Named reviewer and private sign-off evidence are required")
            if decision == "verified" and signed != "yes":
                raise ValueError("Verification requires explicit signed_off=yes")
            judgement = Judgement(
                reviewer=reviewer_id,
                gloss_acceptable=response.get("gloss_acceptable") or None,
                nmm_correct=response.get("nmm_correct") or None,
                comprehension=int(response["comprehension"])
                if response.get("comprehension")
                else None,
                comments=response.get("comments", ""),
                signed_off=signed == "yes",
            )
            matching = next(
                (
                    row
                    for row in existing
                    if row.item_id == ident
                    and row.review_history
                    and row.review_history[0].get("stimulus_sha256") == item["stimulus_sha256"]
                ),
                None,
            )
            if matching and any(j.reviewer == reviewer_id for j in matching.judgements):
                raise ValueError("Reviewer already rated this item; explicit adjudication needed")
            gloss = response.get("reviewed_gloss", "").split()
            nmm = json.loads(response.get("expected_nmm") or "[]")
            if decision == "verified" and (not gloss or len(nmm) != len(gloss)):
                raise ValueError(
                    "Verification requires reviewed gloss and explicitly aligned NMM JSON"
                )
            row = matching or EvalRow(
                item_id=ident,
                english=item["stimulus"]["source_text"],
                source_language=item["stimulus"]["source_language"],
                review_status="in_review",
            )
            row.judgements.append(judgement)
            row.review_history.append(
                {
                    "reviewer_id": reviewer_id,
                    "decision": decision or "in_review",
                    "signed_off": signed == "yes",
                    "evidence_sha256": hashlib.sha256(evidence.encode()).hexdigest()
                    if evidence
                    else None,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "stimulus_sha256": item["stimulus_sha256"],
                    "manifest_sha256": file_hash(directory / "manifest.json"),
                }
            )
            # Name/evidence stay in an explicitly private sidecar, not public metric output.
            if decision == "verified":
                row.expected_gloss = gloss
                row.expected_nmm = [NonManualMarkers.model_validate(value) for value in nmm]
                row.acceptable_alternatives = [
                    g.split()
                    for g in response.get("acceptable_alternatives", "").split("|")
                    if g.strip()
                ]
                row.reviewer = reviewer_id
                row.review_status = "verified"
                row.signer_dialect = response.get("signer_dialect", "")
            elif decision == "rejected":
                row.review_status = "unverified"
            elif row.review_status != "verified":
                row.review_status = "in_review"
            row = EvalRow.model_validate(row.model_dump())
            if matching:
                existing[existing.index(matching)] = row
            else:
                existing.append(row)
        if (file_hash(output) if output.exists() else None) != original_hash:
            raise ValueError("Target changed during review import")
        # Atomic JSONL replacement using a sibling temporary file.
        import os
        import tempfile

        output.parent.mkdir(parents=True, exist_ok=True)
        if reviewer.strip():
            private = output.with_suffix(".identities.private.json")
            identities = json.loads(private.read_text(encoding="utf-8")) if private.exists() else {}
            if reviewer_id in identities and identities[reviewer_id]["name"] != reviewer:
                raise ValueError("Reviewer pseudonym already belongs to a different name")
            identities[reviewer_id] = {"name": reviewer, "evidence": evidence}
            atomic_json(private, identities)
        fd, temporary = tempfile.mkstemp(dir=output.parent, prefix=".review-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write("".join(row.model_dump_json() + "\n" for row in existing))
            os.replace(temporary, output)
        finally:
            Path(temporary).unlink(missing_ok=True)
        atomic_json(
            receipt_path,
            {
                "output_sha256": file_hash(output),
                "manifest_sha256": file_hash(directory / "manifest.json"),
            },
        )
    return existing
