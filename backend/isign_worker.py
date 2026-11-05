"""Private, exact-match iSign worker. Run with uvicorn --app-dir backend."""

import csv
from functools import lru_cache
import math
import os
from pathlib import Path
import re
from secrets import compare_digest

from fastapi import FastAPI, Header, HTTPException

from models.translation import TranslationRequest
from services.isign import sentence_key
from tools.mediapipe_to_clip import convert

app = FastAPI(
    title="Private SignAI research worker", docs_url=None, redoc_url=None, openapi_url=None
)
UID = re.compile(r"[A-Za-z0-9_-]+-[0-9]+")
COMPONENTS = {
    "pose": ("POSE_LANDMARKS", 33),
    "left_hand": ("LEFT_HAND_LANDMARKS", 21),
    "right_hand": ("RIGHT_HAND_LANDMARKS", 21),
}


@lru_cache(maxsize=1)
def index():
    root = Path(os.environ["SIGN_AI_ISIGN_POSES"]).resolve(strict=True)
    poses = {}
    for path in root.rglob("*.pose"):
        if not UID.fullmatch(path.stem):
            continue
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or path.stem in poses:
            raise ValueError("Invalid or ambiguous pose path")
        poses[path.stem] = resolved
    matches = {}
    with Path(os.environ["SIGN_AI_ISIGN_CSV"]).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        uid_column = os.environ.get("SIGN_AI_ISIGN_UID_COLUMN", "uid")
        text_column = os.environ["SIGN_AI_ISIGN_TEXT_COLUMN"]
        if not {uid_column, text_column}.issubset(reader.fieldnames or []):
            raise ValueError("CSV headers do not match configured columns")
        for row in reader:
            uid = (row[uid_column] or "").strip()
            key = sentence_key(row[text_column] or "")
            if uid in poses and key:
                matches.setdefault(key, (uid, poses[uid]))
    if not matches:
        raise ValueError("No transcript UIDs match local pose files")
    return matches


def landmark_frames(pose):
    offsets = {}
    start = 0
    for component in pose.header.components:
        offsets[component.name] = (start, len(component.points))
        start += len(component.points)
    for name, size in COMPONENTS.values():
        if name not in offsets or offsets[name][1] != size:
            raise ValueError("Unsupported pose landmark layout")
    width, height = pose.header.dimensions.width, pose.header.dimensions.height
    fps = float(pose.body.fps)
    data, confidence = pose.body.data, pose.body.confidence
    if not (width > 0 and height > 0 and 0 < fps <= 240 and 2 <= len(data) <= fps * 45):
        raise ValueError("Invalid pose dimensions or duration")
    if data.ndim != 4 or data.shape[1] != 1 or data.shape[-1] != 3:
        raise ValueError("Expected one signer with three-coordinate landmarks")
    frames = []
    for points, scores in zip(data[:, 0], confidence[:, 0], strict=True):
        frame = {}
        for key, (name, size) in COMPONENTS.items():
            offset, _ = offsets[name]
            landmarks = []
            for coords, score in zip(
                points[offset : offset + size], scores[offset : offset + size], strict=True
            ):
                valid = float(score) >= 0.5 and all(math.isfinite(float(value)) for value in coords)
                if valid:
                    x, y, z = map(float, coords)
                    landmarks.append([x / width, y / height, z / width, float(score)])
                else:
                    landmarks.append([0, 0, 0, 0])
            if key == "pose" or all(point[3] for point in landmarks):
                frame[key] = landmarks
        frames.append(frame)
    return {"frames": frames, "width": width, "height": height, "fps": fps}


def decode(uid, path):
    from pose_format import Pose

    with path.open("rb") as stream:
        payload = stream.read(32 * 1024 * 1024 + 1)
    if len(payload) > 32 * 1024 * 1024:
        raise ValueError("Pose exceeds worker size limit")
    data = landmark_frames(Pose.read(payload))
    return convert(data, "ISIGN_SEQUENCE", uid, trim_rest=False, max_keys=360, format=2)


@app.post("/retrieve")
def retrieve(req: TranslationRequest, authorization: str = Header(default="")):
    token = os.environ.get("SIGN_AI_ISIGN_TOKEN", "")
    if len(token) < 32 or not compare_digest(authorization.encode(), f"Bearer {token}".encode()):
        raise HTTPException(401, "Authentication required")
    match = index().get(sentence_key(req.text))
    if match is None:
        return {"match": None}
    uid, path = match
    try:
        clip = decode(uid, path)
    except (ValueError, OSError, SystemExit):
        raise HTTPException(422, "Matched pose could not be retargeted") from None
    return {"match": {"uid": uid, "clip": clip}}
