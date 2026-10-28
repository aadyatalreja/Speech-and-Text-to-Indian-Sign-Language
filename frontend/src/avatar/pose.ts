import { HANDSHAPES, REST_SHAPE } from "./handshapes";
import type { AvatarPose, Curls, HandSpec, HandState, Keyframe, Quat, SignClip, Vec3 } from "./types";

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
  clip: SignClip;
  R: Track<HandState>;
  L: Track<HandState>;
  head: Track<Vec3>;
  brow: Track<number>;
  mouth: Track<number>;
}

function buildTrack<T>(keys: Keyframe[], pick: (k: Keyframe) => T | undefined, fallback: T): Track<T> {
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
  const keys = [...clip.keys].sort((a, b) => a.t - b.t);
  const rest = restPose();
  const hand = (side: "R" | "L") => buildTrack<HandState>(keys, (k) => {
    const h = k[side];
    if (h === undefined) return undefined;
    return h === null ? rest[side] : resolveHand(h);
  }, rest[side]);
  return {
    clip,
    R: hand("R"), L: hand("L"),
    head: buildTrack<Vec3>(keys, (k) => k.head, [0, 0, 0]),
    brow: buildTrack<number>(keys, (k) => k.brow, 0),
    mouth: buildTrack<number>(keys, (k) => k.mouth, 0),
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
});
const mixVec = (a: Vec3, b: Vec3, f: number): Vec3 => [lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f)];
const mixNum = (a: number, b: number, f: number) => lerp(a, b, f);

/** Pose at normalised time t (0..1) inside a compiled clip. Channels a clip never mentions stay at rest. */
export function sampleClip(c: CompiledClip, t: number): AvatarPose {
  const tt = clamp(t, 0, 1);
  return {
    R: sampleTrack(c.R, tt, mixHand),
    L: sampleTrack(c.L, tt, mixHand),
    head: sampleTrack(c.head, tt, mixVec),
    brow: sampleTrack(c.brow, tt, mixNum),
    mouth: sampleTrack(c.mouth, tt, mixNum),
  };
}

/* ---------- smoothing follower (gives co-articulation between signs and hides 50 ms progress steps) ---------- */

export class PoseFollower {
  current: AvatarPose = restPose();

  /** Move `current` towards `target`. `k` is stiffness (1/s): higher = snappier. */
  follow(target: AvatarPose, dt: number, k = 16): AvatarPose {
    const f = 1 - Math.exp(-k * Math.min(dt, 0.1));
    this.current = {
      R: mixHand(this.current.R, target.R, f),
      L: mixHand(this.current.L, target.L, f),
      head: mixVec(this.current.head, target.head, f),
      brow: lerp(this.current.brow, target.brow, f),
      mouth: lerp(this.current.mouth, target.mouth, f),
    };
    return this.current;
  }

  snap(target: AvatarPose) { this.current = target; }
}
