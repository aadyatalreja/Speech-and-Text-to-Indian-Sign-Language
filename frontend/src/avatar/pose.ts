import { HANDSHAPES, REST_SHAPE } from "./handshapes";
import type { AvatarPose, Curls, HandSpec, HandState, KeyframeV2, Quat, SignClip, SignClipV2, FaceChannels, TorsoChannels, FingerJoints, Vec3 } from "./types";

const DEG = Math.PI / 180;
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const smooth = (t: number) => t * t * (3 - 2 * t);

/* ---------- quaternion helpers (no three.js dependency so this file is unit-testable) ---------- */

export function eulerYXZToQuat([pitch, yaw, roll]: Vec3): Quat {
  const x = pitch * DEG * 0.5, y = yaw * DEG * 0.5, z = roll * DEG * 0.5;
  const c1 = Math.cos(x), c2 = Math.cos(y), c3 = Math.cos(z);
  const s1 = Math.sin(x), s2 = Math.sin(y), s3 = Math.sin(z);
  // three.js Euler order "YXZ"
  return [
    s1 * c2 * c3 + c1 * s2 * s3,
    c1 * s2 * c3 - s1 * c2 * s3,
    c1 * c2 * s3 - s1 * s2 * c3,
    c1 * c2 * c3 + s1 * s2 * s3,
  ];
}

export function slerp(a: Quat, b: Quat, t: number): Quat {
  let dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
  let bq = b;
  if (dot < 0) { dot = -dot; bq = [-b[0], -b[1], -b[2], -b[3]]; }
  if (dot > 0.9995) {
    const r: Quat = [lerp(a[0], bq[0], t), lerp(a[1], bq[1], t), lerp(a[2], bq[2], t), lerp(a[3], bq[3], t)];
    return normQ(r);
  }
  const th = Math.acos(dot), s = Math.sin(th);
  const w1 = Math.sin((1 - t) * th) / s, w2 = Math.sin(t * th) / s;
  return [a[0] * w1 + bq[0] * w2, a[1] * w1 + bq[1] * w2, a[2] * w1 + bq[2] * w2, a[3] * w1 + bq[3] * w2];
}

function normQ(q: Quat): Quat {
  const l = Math.hypot(q[0], q[1], q[2], q[3]) || 1;
  return [q[0] / l, q[1] / l, q[2] / l, q[3] / l];
}

/* ---------- rest pose ---------- */

const restHand = (side: "R" | "L"): HandState => {
  const s = side === "R" ? 1 : -1; // R shoulder is at -x, so "inward" is +x
  return {
    p: [-s * 0.7, -1.3, 0.08],
    q: eulerYXZToQuat([0, s * 90, 180]), // fingers down, palm towards the thigh
    c: [...REST_SHAPE] as Curls,
    spread: 0.1,
    thumbOut: 0.2,
  };
};

export const restPose = (): AvatarPose => ({ R: restHand("R"), L: restHand("L"), head: [0, 0, 0], brow: 0, mouth: 0 });

/* ---------- clip compilation & sampling ---------- */

export function resolveHand(spec: HandSpec): HandState {
  const shape = typeof spec.shape === "string" ? HANDSHAPES[spec.shape] ?? HANDSHAPES.flat : spec.shape ?? HANDSHAPES.flat;
  return {
    p: [...spec.p] as Vec3,
    q: spec.q ? normQ(spec.q) : eulerYXZToQuat(spec.rot ?? [0, 0, 0]),
    c: [...shape] as Curls,
    spread: spec.spread ?? 0,
    thumbOut: spec.thumbOut ?? 0.3,
  };
}

interface Track<T> { t: number[]; v: T[] }
export interface CompiledClip {
  activeNmm: (keyof FaceChannels | "head")[];
  clip: SignClip;
  R: Track<HandState>;
  L: Track<HandState>;
  head: Track<Vec3>;
  brow: Track<number>;
  mouth: Track<number>;
  face: Record<keyof FaceChannels, Track<number>>;
  torso: Record<keyof TorsoChannels, Track<number>>;
}

function buildTrack<T>(keys: KeyframeV2[], pick: (k: KeyframeV2) => T | undefined, fallback: T): Track<T> {
  const t: number[] = [], v: T[] = [];
  for (const k of keys) {
    const val = pick(k);
    if (val === undefined) continue;
    t.push(k.t); v.push(val);
  }
  if (!t.length) { t.push(0); v.push(fallback); }
  return { t, v };
}

export function compileClip(clip: SignClip): CompiledClip {
  const adapted = adaptClip(clip);
  const keys = [...adapted.keys].sort((a, b) => a.t - b.t);
  const rest = restPose();
  const previous = { R: rest.R, L: rest.L };
  const hand = (side: "R" | "L") => buildTrack<HandState>(keys, (k) => {
    const h = k[side];
    if (h === undefined) return undefined;
    if (h === null) { previous[side] = rest[side]; return rest[side]; }
    const base = previous[side];
    const resolved = resolveHand({ p: h.p ?? base.p, q: h.wrist ?? h.q ?? (h.rot ? undefined : base.q), rot: h.rot, shape: h.shape ?? base.c, spread: h.spread ?? base.spread, thumbOut: h.thumbOut ?? base.thumbOut });
    resolved.fingers = h.fingers ?? base.fingers;
    previous[side] = resolved;
    return resolved;
  }, rest[side]);
  return {
    clip,
    activeNmm: [
      ...(keys.some(k => k.head != null) ? ["head" as const] : []),
      ...FACE_KEYS.filter(name => keys.some(k => k.face?.[name] != null || legacyFace(k)[name] != null)),
    ],
    R: hand("R"), L: hand("L"),
    head: buildTrack<Vec3>(keys, (k) => k.head, [0, 0, 0]),
    brow: buildTrack<number>(keys, (k) => k.brow, 0),
    mouth: buildTrack<number>(keys, (k) => k.mouth, 0),
    face: Object.fromEntries(FACE_KEYS.map(name => [name, buildTrack<number>(keys, k => k.face?.[name] ?? legacyFace(k)[name], 0)])) as CompiledClip["face"],
    torso: Object.fromEntries(TORSO_KEYS.map(name => [name, buildTrack<number>(keys, k => k.torso?.[name], 0)])) as CompiledClip["torso"],
  };
}

function sampleTrack<T>(tr: Track<T>, t: number, mix: (a: T, b: T, f: number) => T): T {
  const n = tr.t.length;
  if (t <= tr.t[0]) return tr.v[0];
  if (t >= tr.t[n - 1]) return tr.v[n - 1];
  let i = 1;
  while (i < n - 1 && tr.t[i] < t) i++;
  const span = tr.t[i] - tr.t[i - 1] || 1e-6;
  return mix(tr.v[i - 1], tr.v[i], smooth((t - tr.t[i - 1]) / span));
}

const mixHand = (a: HandState, b: HandState, f: number): HandState => ({
  p: [lerp(a.p[0], b.p[0], f), lerp(a.p[1], b.p[1], f), lerp(a.p[2], b.p[2], f)],
  q: slerp(a.q, b.q, f),
  c: a.c.map((x, i) => lerp(x, b.c[i], f)) as Curls,
  spread: lerp(a.spread, b.spread, f),
  thumbOut: lerp(a.thumbOut, b.thumbOut, f),
  ...((a.fingers || b.fingers) ? { fingers: (a.fingers ?? curlJoints(a.c)).map((q, i) => slerp(q, (b.fingers ?? curlJoints(b.c))[i], f)) as FingerJoints } : {}),
});
const mixVec = (a: Vec3, b: Vec3, f: number): Vec3 => [lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f)];
const mixNum = (a: number, b: number, f: number) => lerp(a, b, f);

/** Pose at normalised time t (0..1) inside a compiled clip. Channels a clip never mentions stay at rest. */
export function sampleClip(c: CompiledClip, t: number): AvatarPose {
  const tt = clamp(t, 0, 1);
  return {
    activeNmm: c.activeNmm,
    R: sampleTrack(c.R, tt, mixHand),
    L: sampleTrack(c.L, tt, mixHand),
    head: sampleTrack(c.head, tt, mixVec),
    brow: sampleTrack(c.brow, tt, mixNum),
    mouth: sampleTrack(c.mouth, tt, mixNum),
    face: Object.fromEntries(FACE_KEYS.map(name => [name, sampleTrack(c.face[name], tt, mixNum)])),
    torso: Object.fromEntries(TORSO_KEYS.map(name => [name, sampleTrack(c.torso[name], tt, mixNum)])),
  };
}

/* Engine interpolation only, NOT reviewed ISL coarticulation. */

export function mixPose(a: AvatarPose, b: AvatarPose, fraction: number): AvatarPose {
  const f = clamp(fraction, 0, 1);
  return { activeNmm: f === 0 ? a.activeNmm : f === 1 ? b.activeNmm : [...new Set([...(a.activeNmm ?? []), ...(b.activeNmm ?? [])])],
    R: mixHand(a.R, b.R, f), L: mixHand(a.L, b.L, f), head: mixVec(a.head, b.head, f),
    brow: lerp(a.brow, b.brow, f), mouth: lerp(a.mouth, b.mouth, f),
    face: Object.fromEntries(FACE_KEYS.map(name => [name, lerp(resolvedFace(a)[name] ?? 0, resolvedFace(b)[name] ?? 0, f)])),
    torso: Object.fromEntries(TORSO_KEYS.map(name => [name, lerp(a.torso?.[name] ?? 0, b.torso?.[name] ?? 0, f)])) };
}

/** Blend previous end into the next clip while retaining its current motion. */
export function transitionPose(previous: AvatarPose | null, clip: CompiledClip, t: number, seconds: number, duration: number): AvatarPose {
  const pose = sampleClip(clip, t);
  if (!previous || seconds <= 0 || !Number.isFinite(duration) || duration <= 0) return pose;
  const u = clamp(t * duration / Math.min(seconds, duration / 2), 0, 1);
  const blend = u * u * u * (u * (u * 6 - 15) + 10); // C2 ease: zero endpoint acceleration.
  if (blend <= 0) return previous;
  if (blend >= 1) return pose;
  const mixed = mixPose(previous, pose, blend);
  // Small forward arc, bounded in shoulder widths, to avoid rigid straight-line travel.
  // This is an engine path, not a linguistically reviewed movement modification.
  for (const side of ["R", "L"] as const) {
    const distance = Math.hypot(...pose[side].p.map((v, i) => v - previous[side].p[i]));
    mixed[side].p[2] += Math.min(0.06, distance * 0.1) * 16 * blend ** 2 * (1 - blend) ** 2;
  }
  return mixed;
}

/** Nonlinguistic idle only during holds. Explicit zero is an authored channel too. */
export function idlePose(pose: AvatarPose, seconds: number, holding: boolean): AvatarPose {
  if (!holding) return pose;
  const active = new Set(pose.activeNmm ?? []);
  const face = resolvedFace(pose);
  const phase = ((seconds % 4.6) + 4.6) % 4.6;
  const blink = phase < 0.22 ? Math.sin(Math.PI * phase / 0.22) ** 2 : 0;
  return { ...pose,
    head: active.has("head") || pose.head.some(v => v !== 0) ? pose.head : [Math.sin(seconds * 1.1) * 0.45, Math.sin(seconds * 0.73) * 0.6, Math.sin(seconds * 0.9) * 0.25],
    face: { ...face, eye_blink: active.has("eye_blink") || (face.eye_blink ?? 0) !== 0 ? face.eye_blink : blink },
  };
}

export class PoseFollower {
  current: AvatarPose = restPose();

  /** Move `current` towards `target`. `k` is stiffness (1/s): higher = snappier. */
  follow(target: AvatarPose, dt: number, k = 16): AvatarPose {
    const f = 1 - Math.exp(-k * Math.min(dt, 0.1));
    this.current = mixPose(this.current, target, f);
    return this.current;
  }

  snap(target: AvatarPose) { this.current = target; }
}

export const FACE_KEYS: (keyof FaceChannels)[] = ["mouth_open", "mouth_wide", "mouth_round", "brow_inner_up", "brow_down_left", "brow_down_right", "eye_blink", "gaze_x", "gaze_y"];
export const TORSO_KEYS: (keyof TorsoChannels)[] = ["lean_x", "lean_z", "shoulder_raise_left", "shoulder_raise_right"];
function legacyFace(k: { mouth?: number; brow?: number }): FaceChannels {
  return { mouth_open: k.mouth, brow_inner_up: k.brow == null ? undefined : Math.max(0, k.brow), brow_down_left: k.brow == null ? undefined : Math.max(0, -k.brow), brow_down_right: k.brow == null ? undefined : Math.max(0, -k.brow) };
}
export const resolvedFace = (pose: AvatarPose): FaceChannels => ({ ...legacyFace(pose), ...pose.face });
export function curlJoints(c: Curls): FingerJoints {
  return c.flatMap((value, finger) => (finger === 0 ? [0.5, 0.75, 0.6] : [80 * DEG, 100 * DEG, 60 * DEG]).map(angle => eulerYXZToQuat([clamp(value, 0, 1) * angle / DEG, 0, 0]))) as FingerJoints;
}
/** Additive adapter: v1 data is copied, never rewritten on disk or in caches. */
export function adaptClip(clip: SignClip): SignClipV2 {
  if (clip.version !== 1 && clip.version !== 2) throw new Error("Unsupported clip version");
  if (!Array.isArray(clip.keys) || !clip.keys.length) throw new Error("Clip needs keyframes");
  const result: SignClipV2 = { ...clip, version: 2, keys: clip.keys.map(key => ({ ...key, R: key.R == null ? key.R : { ...key.R }, L: key.L == null ? key.L : { ...key.L } })) };
  if (clip.version === 1) {
    result.keys = clip.keys.map(key => ({ ...key, ...Object.fromEntries((["R", "L"] as const).filter(side => key[side] != null).map(side => {
      const h = resolveHand(key[side]!);
      return [side, { p: h.p, q: h.q, shape: h.c, spread: h.spread, thumbOut: h.thumbOut }];
    })) }));
  }
  if (clip.version === 2) {
    const scalar = (value: number, lo: number, hi: number) => { if (!Number.isFinite(value) || value < lo || value > hi) throw new Error("v2 channel outside rig bounds"); };
    const quaternion = (q: Quat) => { if (!Array.isArray(q) || q.length !== 4 || q.some(v => !Number.isFinite(v)) || Math.hypot(...q) < 1e-6) throw new Error("Invalid joint quaternion"); };
    for (const key of result.keys) {
      scalar(key.t, 0, 1);
      for (const side of ["R", "L"] as const) {
        const hand = key[side];
        if (hand?.wrist) quaternion(hand.wrist);
        if (hand?.q) quaternion(hand.q);
        if (hand?.fingers) { if (hand.fingers.length !== 15) throw new Error("Expected 15 finger joints"); hand.fingers.forEach(quaternion); hand.fingers = hand.fingers.map(normQ) as FingerJoints; }
      }
      for (const [name, value] of Object.entries(key.face ?? {})) {
        if (!FACE_KEYS.includes(name as keyof FaceChannels)) throw new Error("Unknown face channel");
        scalar(value, name.startsWith("gaze_") ? -1 : 0, 1);
      }
      for (const [name, value] of Object.entries(key.torso ?? {})) {
        if (!TORSO_KEYS.includes(name as keyof TorsoChannels)) throw new Error("Unknown torso channel");
        scalar(value, name.startsWith("lean_") ? -30 : 0, name.startsWith("lean_") ? 30 : 0.3);
      }
    }
  }
  return result;
}
