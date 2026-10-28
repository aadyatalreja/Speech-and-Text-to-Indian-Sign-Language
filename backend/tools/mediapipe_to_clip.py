#!/usr/bin/env python3
"""Convert MediaPipe Holistic landmarks of a recorded sign into an avatar clip (SignClip v1).

This is how a *real* sign (from a dataset video or a native signer) reaches the 3D avatar. The
avatar can perform any clip; this script is the bridge from video to clip. No third-party packages.

Input JSON (one file per sign), produced by running MediaPipe Holistic on the video:

    {"fps": 25, "width": 1280, "height": 720,
     "frames": [{"pose": [[x, y, z, visibility] x 33] | null,
                 "left_hand":  [[x, y, z] x 21] | null,    # the signer's left hand
                 "right_hand": [[x, y, z] x 21] | null}]}  # the signer's right hand
    (x, y normalised to 0..1 as MediaPipe returns them; z in MediaPipe's own scale)

Usage:
    python tools/mediapipe_to_clip.py in.json out.json --gloss HELLO --id hello \
        --notes "Source: <dataset>, signer <id>, licence <...>" [--swap-hands] [--max-keys 24]

Then register it in data/signs/signs.json as  "clip": "clips/out.json"  and put the file in
data/signs/clips/. Preview it first in the frontend clip lab (http://localhost:5173/lab.html).

Clip space: origin mid-shoulders, unit = shoulder width, +x viewer right, +y up, +z toward the
viewer (the signer's right hand therefore has negative x). If the video was selfie-mirrored, or the
hands come out swapped in the lab, pass --swap-hands.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from typing import Sequence

Vec = tuple[float, float, float]

# MediaPipe pose landmark ids
NOSE, L_EAR, R_EAR, L_SHOULDER, R_SHOULDER = 0, 7, 8, 11, 12
# MediaPipe hand landmark chains (wrist = 0)
THUMB = (1, 2, 3, 4)
FINGERS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
FULL_CURL_DEG = 240.0   # mcp 80 + pip 100 + dip 60, matches the avatar rig
THUMB_CURL_DEG = 120.0
FAN_DEG_PER_SPREAD = 11.5


# ---------- small vector helpers ----------
def sub(a: Vec, b: Vec) -> Vec: return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a: Vec, b: Vec) -> float: return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a: Vec, b: Vec) -> Vec: return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a: Vec) -> float: return math.sqrt(dot(a, a))
def unit(a: Vec) -> Vec:
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (0.0, 0.0, 0.0)
def clamp(v: float, lo: float, hi: float) -> float: return max(lo, min(hi, v))
def angle_deg(a: Vec, b: Vec) -> float:
    na, nb = norm(a), norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return math.degrees(math.acos(clamp(dot(a, b) / (na * nb), -1.0, 1.0)))


def matrix_to_quat(x: Vec, y: Vec, z: Vec) -> tuple[float, float, float, float]:
    """Rotation matrix with columns x, y, z -> quaternion (x, y, z, w)."""
    m00, m01, m02 = x[0], y[0], z[0]
    m10, m11, m12 = x[1], y[1], z[1]
    m20, m21, m22 = x[2], y[2], z[2]
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        q = (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        q = ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        q = ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)  # type: ignore[return-value]


# ---------- coordinate frame ----------
class Frame:
    """Image landmarks -> clip space (shoulder-width units, origin mid-shoulders)."""

    def __init__(self, width: float, height: float, origin: Vec, shoulder_width: float):
        self.w, self.h, self.o, self.sw = width, height, origin, shoulder_width

    def __call__(self, lm: Sequence[float]) -> Vec:
        px, py, pz = lm[0] * self.w, lm[1] * self.h, lm[2] * self.w
        return ((px - self.o[0]) / self.sw, -(py - self.o[1]) / self.sw, -(pz - self.o[2]) / self.sw)


def build_frame(frames: list[dict], width: float, height: float) -> Frame:
    mids, widths = [], []
    for f in frames:
        pose = f.get("pose")
        if not pose:
            continue
        a, b = pose[L_SHOULDER], pose[R_SHOULDER]
        if min(a[3] if len(a) > 3 else 1, b[3] if len(b) > 3 else 1) < 0.5:
            continue
        pa = (a[0] * width, a[1] * height, a[2] * width)
        pb = (b[0] * width, b[1] * height, b[2] * width)
        mids.append(tuple((pa[i] + pb[i]) / 2 for i in range(3)))
        widths.append(math.hypot(pa[0] - pb[0], pa[1] - pb[1]))  # image-plane width: z is unreliable
    if not mids:
        raise SystemExit("No frame has both shoulders visible; cannot normalise the signer.")
    origin = tuple(statistics.median(m[i] for m in mids) for i in range(3))
    return Frame(width, height, origin, statistics.median(widths))  # type: ignore[arg-type]


# ---------- hand analysis ----------
def hand_state(pts: list[Vec], right: bool) -> dict:
    wrist = pts[0]
    centroid = tuple(sum(pts[i][k] for i in (5, 9, 13, 17)) / 4 for k in range(3))
    fingers_dir = unit(sub(centroid, wrist))                     # wrist -> centre of the knuckles (the rig's finger axis)
    idx, pnk = sub(pts[5], wrist), sub(pts[17], wrist)
    normal = unit(cross(idx, pnk) if right else cross(pnk, idx))  # palm normal (out of the palm)
    x_axis = unit(cross(fingers_dir, normal))
    z_axis = unit(cross(x_axis, fingers_dir))                     # re-orthogonalise
    q = matrix_to_quat(x_axis, fingers_dir, z_axis)

    curls = []
    thumb = [pts[i] for i in THUMB]
    t_ang = angle_deg(sub(thumb[1], thumb[0]), sub(thumb[2], thumb[1])) + angle_deg(sub(thumb[2], thumb[1]), sub(thumb[3], thumb[2]))
    curls.append(clamp(t_ang / THUMB_CURL_DEG, 0, 1))
    dirs = []
    for chain in FINGERS:
        mcp, pip, dip, tip = (pts[i] for i in chain)
        total = (angle_deg(sub(mcp, wrist), sub(pip, mcp)) + angle_deg(sub(pip, mcp), sub(dip, pip)) + angle_deg(sub(dip, pip), sub(tip, dip)))
        curls.append(clamp(total / FULL_CURL_DEG, 0, 1))
        dirs.append(sub(pip, mcp))
    fan = statistics.mean(angle_deg(dirs[i], dirs[i + 1]) for i in range(3))
    spread = clamp((fan - 3.0) / FAN_DEG_PER_SPREAD, 0, 1.5)
    thumb_out = clamp((angle_deg(sub(thumb[1], thumb[0]), sub(pts[5], wrist)) - 10.0) / 55.0, 0, 1)
    return {"p": wrist, "q": q, "c": curls, "spread": spread, "thumbOut": thumb_out}


def head_angles(pose: list[list[float]], width: float, height: float) -> tuple[float, float] | None:
    try:
        nose, le, re = pose[NOSE], pose[L_EAR], pose[R_EAR]
    except IndexError:
        return None
    if min(p[3] if len(p) > 3 else 1 for p in (nose, le, re)) < 0.5:
        return None
    ear_dx = abs(le[0] - re[0]) * width
    if ear_dx < 1e-6:
        return None
    mid_x, mid_y = (le[0] + re[0]) / 2 * width, (le[1] + re[1]) / 2 * height
    yaw = math.degrees(math.asin(clamp((nose[0] * width - mid_x) / (ear_dx * 0.6), -1, 1)))
    pitch_raw = math.degrees(math.atan2(nose[1] * height - mid_y, ear_dx))
    return yaw, pitch_raw


# ---------- smoothing / filling ----------
def fill(values: list):
    """Forward then backward fill None entries; returns None if nothing is valid."""
    if all(v is None for v in values):
        return None
    out = list(values)
    last = None
    for i, v in enumerate(out):
        last = v if v is not None else last
        out[i] = last
    nxt = None
    for i in range(len(out) - 1, -1, -1):
        nxt = out[i] if out[i] is not None else nxt
        out[i] = nxt
    return out


def smooth_hand(seq: list[dict], radius: int = 2) -> list[dict]:
    out = []
    for i in range(len(seq)):
        win = seq[max(0, i - radius): i + radius + 1]
        ref_q = seq[i]["q"]
        qs = []
        for h in win:  # align quaternion signs before averaging
            sign = 1.0 if sum(a * b for a, b in zip(h["q"], ref_q)) >= 0 else -1.0
            qs.append([sign * c for c in h["q"]])
        q = [statistics.mean(c) for c in zip(*qs)]
        n = math.sqrt(sum(c * c for c in q)) or 1.0
        out.append({
            "p": tuple(statistics.mean(h["p"][k] for h in win) for k in range(3)),
            "q": tuple(c / n for c in q),
            "c": [statistics.mean(h["c"][k] for h in win) for k in range(5)],
            "spread": statistics.mean(h["spread"] for h in win),
            "thumbOut": statistics.mean(h["thumbOut"] for h in win),
        })
    return out


def spec(h: dict) -> dict:
    r = lambda v: round(v, 3)
    return {"p": [r(v) for v in h["p"]], "q": [round(v, 4) for v in h["q"]], "shape": [r(v) for v in h["c"]],
            "spread": r(h["spread"]), "thumbOut": r(h["thumbOut"])}


# ---------- main conversion ----------
def convert(data: dict, gloss: str, clip_id: str, notes: str = "", swap_hands: bool = False,
            max_keys: int = 24, min_detect: float = 0.3, trim_rest: bool = True) -> dict:
    frames = data["frames"]
    if len(frames) < 2:
        raise SystemExit("Need at least 2 frames.")
    W, H = float(data.get("width", 1280)), float(data.get("height", 720))
    fr = build_frame(frames, W, H)

    keymap = {"right_hand": "R", "left_hand": "L"}
    if swap_hands:
        keymap = {"right_hand": "L", "left_hand": "R"}
    tracks: dict[str, list] = {"R": [], "L": []}
    for f in frames:
        for src, dst in keymap.items():
            lm = f.get(src)
            tracks[dst].append(hand_state([fr(p) for p in lm], right=(src == "right_hand")) if lm and len(lm) == 21 else None)

    n = len(frames)
    kept: dict[str, list[dict]] = {}
    for side, seq in tracks.items():
        if sum(v is not None for v in seq) / n < min_detect:
            continue
        filled = smooth_hand(fill(seq))  # type: ignore[arg-type]
        if max(h["p"][1] for h in filled) < -0.9:   # hanging at the side the whole time: leave at rest
            continue
        kept[side] = filled
    if not kept:
        raise SystemExit("No hand was detected in enough frames.")

    head = None
    raw = [head_angles(f["pose"], W, H) if f.get("pose") else None for f in frames]
    raw = fill(raw)
    if raw:
        base_pitch = statistics.median(p for _, p in raw)
        head = [(clamp(y, -35, 35), clamp(p - base_pitch, -30, 30)) for y, p in raw]

    first, last = 0, n - 1
    if trim_rest:
        def active(i: int) -> bool:
            return any(h[i]["p"][1] > -0.9 for h in kept.values())
        while first < last and not active(first): first += 1
        while last > first and not active(last): last -= 1
    idxs = list(range(first, last + 1))
    if len(idxs) > max_keys:
        idxs = [first + round(k * (last - first) / (max_keys - 1)) for k in range(max_keys)]
    span = max(1, last - first)

    keys = []
    for i in idxs:
        k: dict = {"t": round((i - first) / span, 4)}
        for side, seq in kept.items():
            k[side] = spec(seq[i])
        if head:
            k["head"] = [round(head[i][1], 1), round(head[i][0], 1), 0]
        keys.append(k)
    dur = (last - first) / float(data.get("fps", 25))
    return {"version": 1, "id": clip_id, "gloss": gloss.upper(), "kind": "dataset", "keys": keys,
            "notes": (notes + f" | converted from {len(frames)} frames, {dur:.2f}s").strip(" |")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--gloss", required=True); ap.add_argument("--id")
    ap.add_argument("--notes", default="", help="source, signer, licence, review status")
    ap.add_argument("--swap-hands", action="store_true")
    ap.add_argument("--max-keys", type=int, default=24)
    ap.add_argument("--no-trim", action="store_true", help="keep idle frames at the start and end")
    a = ap.parse_args(argv)
    with open(a.input, encoding="utf-8") as f:
        data = json.load(f)
    clip = convert(data, a.gloss, a.id or a.gloss.lower(), a.notes, a.swap_hands, a.max_keys, trim_rest=not a.no_trim)
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(clip, f, separators=(",", ":"))
    print(f"wrote {a.output}: {len(clip['keys'])} keyframes, hands: {sorted(k for k in clip['keys'][0] if k in ('R', 'L'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
