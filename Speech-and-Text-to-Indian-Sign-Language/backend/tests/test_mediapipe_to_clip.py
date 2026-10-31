import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mediapipe_to_clip as m  # noqa: E402

W = H = 1.0
SW, MID = 0.4, (0.5, 0.4)  # shoulder width and mid-shoulder point in image units


def to_img(v):
    """clip space -> MediaPipe-style image landmark (inverse of m.Frame)."""
    return [MID[0] + v[0] * SW, MID[1] - v[1] * SW, -v[2] * SW]


def chain(base, dirs, lens):
    pts, p = [], base
    for d, l in zip(dirs, lens):
        p = (p[0] + d[0] * l, p[1] + d[1] * l, p[2] + d[2] * l)
        pts.append(p)
    return pts


def hand(curl: float, right=True, rot=None, at=(0.0, 0.0, 0.0)):
    """Canonical hand in clip space: fingers +y, palm normal +z, thumb on +x for the right hand."""
    s = 1 if right else -1
    thumb = [(s * 0.07, 0.05, 0.02), (s * 0.12, 0.12, 0.04), (s * 0.15, 0.19, 0.05), (s * 0.17, 0.25, 0.05)]
    pts = [(0.0, 0.0, 0.0)] + thumb
    for x, base_y, lens in [(0.09, 0.28, (0.12, 0.08, 0.07)), (0.03, 0.29, (0.13, 0.09, 0.07)), (-0.03, 0.28, (0.12, 0.08, 0.07)), (-0.09, 0.26, (0.10, 0.07, 0.06))]:
        base = (s * x, base_y, 0.0)
        a1, a2, a3 = (math.radians(curl * d) for d in (80, 180, 240))  # cumulative flexion
        dirs = [(0, math.cos(a1), math.sin(a1)), (0, math.cos(a2), math.sin(a2)), (0, math.cos(a3), math.sin(a3))]
        pts += [base] + chain(base, dirs, lens)
    if rot:
        pts = [rot(p) for p in pts]
    return [to_img((p[0] + at[0], p[1] + at[1], p[2] + at[2])) for p in pts]


def ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return lambda p: (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def pose():
    p = [[0.0, 0.0, 0.0, 1.0] for _ in range(33)]
    p[m.L_SHOULDER] = [MID[0] + SW / 2, MID[1], 0.0, 1.0]
    p[m.R_SHOULDER] = [MID[0] - SW / 2, MID[1], 0.0, 1.0]
    p[m.NOSE] = [0.5, 0.25, 0.0, 1.0]
    p[m.L_EAR] = [0.55, 0.24, 0.0, 1.0]
    p[m.R_EAR] = [0.45, 0.24, 0.0, 1.0]
    return p


def frames(n, make_right, make_left=None):
    out = []
    for i in range(n):
        f = {"pose": pose(), "right_hand": make_right(i / (n - 1))}
        if make_left:
            f["left_hand"] = make_left(i / (n - 1))
        out.append(f)
    return {"fps": 25, "width": W, "height": H, "frames": out}


def test_flat_hand_is_identity_with_zero_curl():
    st = m.hand_state([m.Frame(W, H, (MID[0], MID[1], 0.0), SW)(p) for p in hand(0.0)], right=True)
    assert [round(v, 3) for v in st["q"]] == [0.0, 0.0, 0.0, 1.0]
    assert max(st["c"][1:]) < 0.1


def test_fist_has_full_curl():
    st = m.hand_state([m.Frame(W, H, (MID[0], MID[1], 0.0), SW)(p) for p in hand(1.0)], right=True)
    assert min(st["c"][1:]) > 0.95


def test_orientation_recovered_for_yaw_180_right_and_left():
    fr = m.Frame(W, H, (MID[0], MID[1], 0.0), SW)
    for right in (True, False):
        st = m.hand_state([fr(p) for p in hand(0.0, right=right, rot=ry(180))], right=right)
        # 180 degrees about y == quaternion (0, ±1, 0, 0)
        assert abs(abs(st["q"][1]) - 1.0) < 1e-3, (right, st["q"])
    st = m.hand_state([fr(p) for p in hand(0.0, rot=ry(90))], right=True)
    assert abs(st["q"][1] - math.sin(math.radians(45))) < 1e-3 and abs(st["q"][3] - math.cos(math.radians(45))) < 1e-3


def test_left_hand_canonical_is_identity_too():
    fr = m.Frame(W, H, (MID[0], MID[1], 0.0), SW)
    st = m.hand_state([fr(p) for p in hand(0.0, right=False)], right=False)
    assert [round(v, 3) for v in st["q"]] == [0.0, 0.0, 0.0, 1.0]


def test_convert_moving_curling_hand():
    data = frames(60, lambda t: hand(t, at=(-0.3, -0.2 + 0.8 * t, 0.4)))
    clip = m.convert(data, "test", "test", "unit test", max_keys=10)
    assert clip["version"] == 1 and clip["kind"] == "dataset" and clip["gloss"] == "TEST"
    assert len(clip["keys"]) == 10
    assert clip["keys"][0]["t"] == 0 and clip["keys"][-1]["t"] == 1
    r0, r1 = clip["keys"][0]["R"], clip["keys"][-1]["R"]
    assert r0["p"][0] < 0                      # signer's right hand is at viewer-left (negative x)
    assert r1["p"][1] > r0["p"][1]             # moved up
    assert r1["shape"][1] > r0["shape"][1] + 0.5   # index curled over the clip
    assert "L" not in clip["keys"][0]          # hand never detected -> left at rest
    assert "head" in clip["keys"][0]
    json.dumps(clip)


def test_swap_hands_and_idle_hand_is_dropped():
    low = lambda t: hand(0.0, right=False, at=(0.6, -1.4, 0.1))  # hanging at the side
    data = frames(30, lambda t: hand(0.0, at=(-0.3, 0.0, 0.4)), low)
    clip = m.convert(data, "x", "x")
    assert "R" in clip["keys"][0] and "L" not in clip["keys"][0]
    swapped = m.convert(data, "x", "x", swap_hands=True)
    assert "L" in swapped["keys"][0] and "R" not in swapped["keys"][0]


def test_cli_roundtrip(tmp_path):
    src, dst = tmp_path / "in.json", tmp_path / "out.json"
    src.write_text(json.dumps(frames(20, lambda t: hand(0.0, at=(-0.3, t, 0.4)))))
    assert m.main([str(src), str(dst), "--gloss", "hello", "--notes", "synthetic"]) == 0
    out = json.loads(dst.read_text())
    assert out["gloss"] == "HELLO" and out["notes"].startswith("synthetic")
