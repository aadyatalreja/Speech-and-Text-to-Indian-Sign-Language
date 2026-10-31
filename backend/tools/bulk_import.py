"""Import licensed local videos or precomputed Holistic landmarks into signs.json.

No dataset downloads. Every source needs an explicit permissions record. Each
row commits independently; successful rows survive failures and can be resumed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import statistics
import sys
import tempfile
from contextlib import contextmanager

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from models.sign import ClipQA, Sign
from services.sign_repository import JsonSignRepository, normalize_text
from tools import mediapipe_to_clip as converter
from tools.validate_signs import validate_signs, _unique_object

log = logging.getLogger("signai.import")
REQUIRED = {"gloss", "aliases", "category", "video_path", "source", "licence", "signer"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".import-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def local_target(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Output path escapes sign folder")
    return target


def check_permissions(row, approvals, intended_use):
    record = approvals.get(row["source"])
    if not isinstance(record, dict) or record.get("licence") != row["licence"]:
        raise ValueError("Source/licence has no matching permissions record")
    if record.get("intended_use") != intended_use or record.get("allow_processing") is not True or record.get("allow_redistribution") is not True:
        raise ValueError("Permissions must allow intended use and redistribution of video/derived clips")
    if not all(isinstance(record.get(key), str) and record[key].strip() for key in ("reviewer", "evidence")):
        raise ValueError("Permissions require reviewer and evidence")
    return record


def validate_landmarks(data):
    if not isinstance(data, dict):
        raise ValueError("Landmarks must be an object")
    for name in ("fps", "width", "height"):
        value = data.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid landmark {name}")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) < 2:
        raise ValueError("At least two landmark frames required")
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Invalid landmark frame")
        for name, length, dimensions in (("pose", 33, 4), ("left_hand", 21, 3), ("right_hand", 21, 3)):
            landmarks = frame.get(name)
            if landmarks is None:
                continue
            if not isinstance(landmarks, list) or len(landmarks) != length or any(
                not isinstance(point, list) or len(point) < dimensions or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in point) for point in landmarks):
                raise ValueError(f"Malformed {name} landmarks")
    # Converter normalization needs visible, non-coincident shoulders.
    coordinate_frame = converter.build_frame(frames, data["width"], data["height"])
    if coordinate_frame.sw < 1e-6:
        raise ValueError("Degenerate shoulder width")


def extract_video(path):
    """Optional legacy Holistic adapter, pinned separately from backend runtime."""
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise ValueError("Video extraction needs backend/requirements-ingest.txt") from exc
    if not hasattr(mp, "solutions"):
        raise ValueError("This adapter needs the pinned MediaPipe legacy Holistic API; see requirements-ingest.txt")
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError("Cannot open video")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        expected = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0 or min(width, height) <= 0:
            raise ValueError("Video has invalid fps/dimensions")
        frames = []
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=1,
                smooth_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                result = holistic.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                def points(value, visibility=False):
                    return None if value is None else [[p.x, p.y, p.z, *([p.visibility] if visibility else [])] for p in value.landmark]
                frames.append({"pose": points(result.pose_landmarks, True),
                    "left_hand": points(result.left_hand_landmarks), "right_hand": points(result.right_hand_landmarks)})
        if expected > 0 and len(frames) < expected - 1:
            raise ValueError(f"Video decoding stopped early ({len(frames)}/{expected} frames)")
        return {"fps": fps, "width": width, "height": height, "frames": frames}
    finally:
        capture.release()


def clip_qa(data, clip):
    frames = data["frames"]
    ratios = {name: sum(bool(frame.get(name)) for frame in frames) / len(frames)
              for name in ("pose", "left_hand", "right_hand")}
    both = sum(bool(frame.get("left_hand")) and bool(frame.get("right_hand")) for frame in frames) / len(frames)
    coordinate_frame = converter.build_frame(frames, data["width"], data["height"])
    acceleration = []
    for side in ("left_hand", "right_hand"):
        wrists = [coordinate_frame(frame[side][0]) if frame.get(side) else None for frame in frames]
        for a, b, c in zip(wrists, wrists[1:], wrists[2:]):
            if a is not None and b is not None and c is not None:
                acceleration.append(math.sqrt(sum((c[i] - 2 * b[i] + a[i]) ** 2 for i in range(3))))
    jitter = statistics.mean(acceleration) if acceleration else 0.0
    score = 0.6 * both + 0.2 * ratios["pose"] + 0.2 * max(0, 1 - jitter / 0.15)
    return ClipQA(both_hands_fraction=both, left_hand_fraction=ratios["left_hand"],
        right_hand_fraction=ratios["right_hand"], pose_fraction=ratios["pose"], jitter=jitter,
        frame_count=len(frames), key_count=len(clip["keys"]), duration=clip["duration"], score=round(score, 6))


def _import_manifest(manifest, output, permissions, intended_use, *, copy_video=False,
                    force=False, max_keys=24, qa_threshold=0.75, swap_hands=False, extractor=None):
    if max_keys < 2 or not 0 <= qa_threshold <= 1:
        raise ValueError("max_keys must be >=2 and qa_threshold must be 0..1")
    manifest, root = Path(manifest).resolve(), Path(output).resolve()
    approvals = read_json(permissions)
    if not isinstance(approvals, dict):
        raise ValueError("Permissions must be keyed by exact source")
    root.mkdir(parents=True, exist_ok=True)
    database = root / "signs.json"
    if database.exists():
        JsonSignRepository(database)
    raw = read_json(database) if database.exists() else {}
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("CSV requires columns: " + ", ".join(sorted(REQUIRED)))
        rows = list(reader)
    summary = {"imported": [], "skipped": [], "protected": [], "errors": []}
    seen = set()
    code_hash = file_hash(Path(__file__)) + file_hash(Path(converter.__file__))
    for line, row in enumerate(rows, 2):
        try:
            snapshot = database.read_bytes() if database.exists() else None
            database_hash = hashlib.sha256(snapshot).hexdigest() if snapshot is not None else None
            raw = json.loads(snapshot, object_pairs_hook=_unique_object) if snapshot is not None else {}
            if None in row or any(row.get(field) is None for field in REQUIRED):
                raise ValueError("Malformed CSV row")
            row = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
            gloss = re.sub(r"\s+", "_", row["gloss"].upper())
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9_]*", gloss):
                raise ValueError("Gloss must use letters/digits/underscores")
            if gloss in seen:
                raise ValueError("Duplicate gloss in manifest")
            seen.add(gloss)
            if not all(row[field] for field in ("source", "licence", "signer")):
                raise ValueError("Source, licence, and signer are required")
            permission = check_permissions(row, approvals, intended_use)
            existing = raw.get(gloss)
            if existing and existing.get("review_status") == "verified" and not force:
                summary["protected"].append(gloss)
                log.warning("%s protected: verified entry; --force required", gloss)
                continue
            aliases = json.loads(row["aliases"]) if row["aliases"].startswith("[") else [a.strip() for a in row["aliases"].split("|") if a.strip()]
            if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases) or len({normalize_text(a) for a in aliases}) != len(aliases):
                raise ValueError("Aliases must be distinct strings (pipe-separated or JSON list)")
            video = (manifest.parent / row["video_path"]).resolve() if row["video_path"] else None
            landmarks_source = (manifest.parent / row["landmarks_path"]).resolve() if row.get("landmarks_path") else None
            if not landmarks_source and not video:
                raise ValueError("video_path or landmarks_path required")
            if copy_video and not video:
                raise ValueError("--copy-video requires video_path")
            inputs = [path for path in (video, landmarks_source) if path is not None]
            hashes = {str(path): file_hash(path) for path in inputs}
            fingerprint = hashlib.sha256(json.dumps({"row": row, "inputs": hashes, "permission": permission,
                "intended_use": intended_use, "copy_video": copy_video, "max_keys": max_keys,
                "qa_threshold": qa_threshold, "swap_hands": swap_hands, "code": code_hash}, sort_keys=True).encode()).hexdigest()
            if existing and existing.get("import_fingerprint") == fingerprint and existing.get("import_files") and not (
                force and existing.get("review_status") == "verified") and all(
                local_target(root, name).is_file() and file_hash(local_target(root, name)) == digest
                for name, digest in existing["import_files"].items()):
                summary["skipped"].append(gloss)
                log.info("%s unchanged; skipped", gloss)
                continue
            stem = f"{gloss.lower()}_{fingerprint[:16]}"
            landmark_path = local_target(root, f"landmarks/{stem}.json")
            if landmarks_source:
                data = read_json(landmarks_source)
            elif landmark_path.is_file():
                data = read_json(landmark_path)
                log.info("%s resuming cached landmarks", gloss)
            else:
                data = (extractor or extract_video)(video)
            validate_landmarks(data)
            # Keep completed extraction before conversion so an interrupted row
            # can reuse it. No registry entry references incomplete artifacts.
            atomic_json(landmark_path, data)
            metadata = {key: row[key] for key in ("source", "licence", "signer")}
            clip = converter.convert(data, gloss, existing["id"] if existing else gloss.lower(),
                "Unverified conversion; native-signer review required", swap_hands=swap_hands, max_keys=max_keys)
            qa = clip_qa(data, clip)
            clip.update(metadata, review_status="unverified", qa=qa.model_dump())
            entry = {**(existing or {}), "id": clip["id"], "gloss": gloss, "aliases": aliases,
                "category": row["category"] or None, "asset_type": "dataset", "clip": f"clips/{stem}.json",
                "keypoints": f"landmarks/{stem}.json", "video": None, **metadata,
                "review_status": "unverified", "qa": qa.model_dump(), "duration": qa.duration,
                "reviewer": None, "review_decision": None, "clip_review_decision": None,
                "video_duration": len(data["frames"]) / data["fps"] if copy_video else None,
                "needs_manual_review": qa.score < qa_threshold, "import_fingerprint": fingerprint,
                "notes": "Imported; not verified ISL. QA is a technical heuristic, not signer review.",
                "permission_review": permission, "intended_use": intended_use}
            Sign(**entry)
            candidate = {**raw, gloss: entry}
            with tempfile.TemporaryDirectory(prefix=".import-check-", dir=root) as temporary:
                candidate_path = Path(temporary) / "signs.json"
                atomic_json(candidate_path, candidate)
                JsonSignRepository(candidate_path)  # reject alias/id conflicts before publishing files
            clip_path = local_target(root, entry["clip"])
            atomic_json(clip_path, clip)
            published = [clip_path, landmark_path]
            if copy_video:
                if not re.fullmatch(r"\.[A-Za-z0-9]+", video.suffix):
                    raise ValueError("Video needs a file extension")
                destination = local_target(root, f"video/{stem}{video.suffix.lower()}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Atomic copy: a crash cannot expose a partial final video.
                handle, temp_name = tempfile.mkstemp(prefix=".import-", dir=destination.parent)
                try:
                    import shutil
                    with video.open("rb") as source, os.fdopen(handle, "wb") as target:
                        shutil.copyfileobj(source, target)
                    os.replace(temp_name, destination)
                finally:
                    Path(temp_name).unlink(missing_ok=True)
                entry["video"] = destination.relative_to(root).as_posix()
                published.append(destination)
            entry["import_files"] = {path.relative_to(root).as_posix(): file_hash(path) for path in published}
            # Validate the candidate in the same root so relative references and
            # the alphabet manifest are checked before atomic registry replace.
            handle, check_name = tempfile.mkstemp(prefix=".candidate-", suffix=".json", dir=root)
            os.close(handle)
            check_path = Path(check_name)
            try:
                atomic_json(check_path, candidate)
                if errors := validate_signs(check_path):
                    raise ValueError("Candidate failed validation: " + "; ".join(errors))
            finally:
                check_path.unlink(missing_ok=True)
            if (file_hash(database) if database.exists() else None) != database_hash:
                raise ValueError("Database changed during import; retry against the updated registry")
            atomic_json(database, candidate)
            raw = candidate
            summary["imported"].append(gloss)
            log.info("%s imported: QA %.3f, manual flag=%s, unverified", gloss, qa.score, entry["needs_manual_review"])
        except (Exception, SystemExit) as exc:
            summary["errors"].append({"line": line, "gloss": row.get("gloss"), "error": str(exc)})
            log.error("CSV line %s failed: %s", line, exc)
    if database.exists() and (errors := validate_signs(database)):
        summary["errors"].append({"line": None, "gloss": None, "error": "Database validation: " + "; ".join(errors)})
    return summary


@contextmanager
def registry_lock(output):
    """Single writer lock, automatically released by the OS after a crash."""
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".bulk-import.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Another import is active for this sign folder") from exc
        try:
            yield root
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def import_manifest(manifest, output, permissions, intended_use, **options):
    with registry_lock(output) as root:
        return _import_manifest(manifest, root, permissions, intended_use, **options)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=settings.SIGN_DATA_PATH)
    parser.add_argument("--permissions", type=Path, required=True)
    parser.add_argument("--intended-use", required=True)
    parser.add_argument("--copy-video", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--swap-hands", action="store_true")
    parser.add_argument("--max-keys", type=int, default=24)
    parser.add_argument("--qa-threshold", type=float, default=0.75)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        summary = import_manifest(args.manifest, args.output, args.permissions, args.intended_use,
            copy_video=args.copy_video, force=args.force, max_keys=args.max_keys,
            qa_threshold=args.qa_threshold, swap_hands=args.swap_hands)
        print(json.dumps(summary, indent=2))
        return 1 if summary["errors"] else 0
    except (Exception, SystemExit) as exc:
        log.error("Import failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
