"""Validate sign metadata and local references; does not certify licensing or ISL.

Run from any directory: python backend/tools/validate_signs.py [signs.json]
"""
import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError
from config import settings
from models.sign import Sign
from models.alphabet import AlphabetManifest
from models.markers import NonManualMarkers
from services.sign_repository import normalize_text


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_alphabet(path: Path | str) -> list[str]:
    path = Path(path)
    try:
        manifest = AlphabetManifest.model_validate(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object))
    except (OSError, ValueError) as exc:
        return [f"Invalid alphabet manifest: {exc}"]
    errors = []
    for symbol, entry in manifest.characters.items():
        if not entry.clip:
            continue
        target = (path.parent / entry.clip).resolve()
        if not target.is_relative_to(path.parent.resolve()):
            errors.append(f"Alphabet {symbol}: clip escapes alphabet folder")
            continue
        try:
            clip = json.loads(target.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if clip.get("version") != 1 or clip.get("kind") != "dataset" or clip.get("gloss") != symbol:
                raise ValueError("Expected SignClip v1 dataset with matching character gloss")
            keys = clip.get("keys")
            if not isinstance(keys, list) or not keys:
                raise ValueError("Clip requires keyframes")
            previous = -1
            for key in keys:
                t = key.get("t")
                if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 0 <= t <= 1 or t < previous:
                    raise ValueError("Key times must be finite, ordered, and in 0..1")
                previous = t
                NonManualMarkers(**{k: key[k] for k in ("head", "brow", "mouth") if k in key})
                for side in ("L", "R"):
                    hand = key.get(side)
                    if hand is None:
                        continue
                    for channel, size in (("p", 3), ("rot", 3), ("q", 4)):
                        values = hand.get(channel)
                        if values is None and channel != "p":
                            continue
                        if not isinstance(values, list) or len(values) != size or any(
                            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
                            raise ValueError(f"Invalid {side}.{channel}")
                    if "q" in hand and not any(hand["q"]):
                        raise ValueError("Zero hand quaternion")
                    shape = hand.get("shape")
                    presets = {"flat", "open", "fist", "point", "two", "three", "four", "claw", "cee", "oh", "flatO", "ell", "why", "thumbUp", "pinkyUp", "okay", "hook", "relaxed"}
                    if shape is not None and (shape not in presets if isinstance(shape, str) else
                        not isinstance(shape, list) or len(shape) != 5 or any(isinstance(v, bool) or
                        not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in shape)):
                        raise ValueError("Invalid alphabet handshape")
                    for channel, low, high in (("spread", -1, 1), ("thumbOut", 0, 1)):
                        value = hand.get(channel)
                        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or
                            not math.isfinite(value) or not low <= value <= high):
                            raise ValueError(f"Invalid alphabet {channel}")
            if not any(key.get("L") or key.get("R") for key in keys):
                raise ValueError("Alphabet clip contains no hand data")
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f"Alphabet {symbol}: invalid/missing clip: {exc}")
    return errors


def validate_signs(path: Path | str) -> list[str]:
    """Return all discovered errors. Legacy demos need no provenance claims."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError) as exc:
        return [f"Cannot read sign database: {exc}"]
    if not isinstance(raw, dict):
        return ["Sign database must be an object keyed by gloss."]
    errors = []
    ids = {}
    names = {}
    root = path.parent.resolve()
    for key, entry in raw.items():
        try:
            if not isinstance(entry, dict):
                raise ValueError("entry must be an object")
            sign = Sign(**entry)
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(f"{key}: invalid sign schema: {exc}")
            continue
        if normalize_text(key) != normalize_text(sign.gloss):
            errors.append(f"{key}: key does not match gloss {sign.gloss}")
        ident = normalize_text(sign.id)
        if not ident:
            errors.append(f"{key}: empty id")
        elif ident in ids:
            errors.append(f"{key}: duplicate id {sign.id} (also {ids[ident]})")
        ids[ident] = key
        # A gloss and its own lemma/alias may coincide; cross-entry collisions
        # and repeated explicit aliases are errors.
        aliases = set()
        for alias in sign.aliases:
            name = normalize_text(alias)
            if not name or name in aliases:
                errors.append(f"{key}: empty or duplicate alias {alias!r}")
            aliases.add(name)
        for label in [key, sign.gloss, *sign.aliases, *([sign.lemma] if sign.lemma else [])]:
            name = normalize_text(label)
            if not name:
                errors.append(f"{key}: empty lookup name")
            elif name in names and names[name] != key:
                errors.append(f"{key}: duplicate alias/lookup name {label!r} (also {names[name]})")
            names[name] = key
        if sign.asset_type != "demo":
            for field in ("source", "licence", "signer"):
                if not (getattr(sign, field) or "").strip():
                    errors.append(f"{key}: non-demo asset requires {field}")
            if "review_status" not in entry:
                errors.append(f"{key}: non-demo asset requires explicit review_status")
        for field in ("video", "clip", "keypoints"):
            reference = getattr(sign, field)
            if reference is None:
                continue
            target = (root / reference).resolve()
            if not reference.strip() or Path(reference).is_absolute() or not target.is_relative_to(root):
                errors.append(f"{key}: {field} must be a relative file inside {root}")
            elif not target.is_file():
                errors.append(f"{key}: missing {field} file: {reference}")
    alphabet = root / "alphabet" / "manifest.json"
    if alphabet.is_file():
        errors.extend(validate_alphabet(alphabet))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=settings.SIGN_DATA_PATH / "signs.json")
    args = parser.parse_args(argv)
    errors = validate_signs(args.path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Sign metadata and file references are valid (ISL and licence permissions not certified).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
