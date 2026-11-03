import type { NonManualMarkers } from "../types/translation";
import { adaptClip } from "./pose";
import type { KeyframeV2, SignClip, Vec3 } from "./types";

/** Rig channel validation, not a linguistic rule or sign definition. */
export function parseNmm(raw: unknown): NonManualMarkers {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("NMM must be an object");
  const value = raw as Record<string, unknown>;
  if (Object.keys(value).some((key) => !["brow", "head", "mouth", "gaze", "mouth_shape"].includes(key))) throw new Error("Unknown NMM channel");
  const number = (v: unknown, min: number, max: number): number => {
    if (typeof v !== "number" || !Number.isFinite(v) || v < min || v > max) throw new Error(`NMM value must be ${min}..${max}`);
    return v;
  };
  const result: NonManualMarkers = {};
  if (value.brow != null) result.brow = number(value.brow, -1, 1);
  if (value.mouth != null) result.mouth = number(value.mouth, 0, 1);
  if (value.head != null) {
    if (!Array.isArray(value.head) || value.head.length !== 3) throw new Error("NMM head requires three angles");
    result.head = value.head.map((angle) => number(angle, -90, 90)) as Vec3;
  }
  if (value.gaze != null) {
    if (!Array.isArray(value.gaze) || value.gaze.length !== 2) throw new Error("NMM gaze requires two coordinates");
    result.gaze = value.gaze.map(v => number(v, -1, 1)) as [number, number];
  }
  if (value.mouth_shape != null) {
    if (typeof value.mouth_shape !== "object" || Array.isArray(value.mouth_shape)) throw new Error("Invalid mouth_shape");
    const shape = value.mouth_shape as Record<string, unknown>;
    if (Object.keys(shape).some(k => !["open", "wide", "round"].includes(k))) throw new Error("Unknown mouth shape channel");
    result.mouth_shape = Object.fromEntries(Object.entries(shape).filter(([, v]) => v != null).map(([k, v]) => [k, number(v, 0, 1)]));
  }
  return result;
}

/** Override only configured channels across the sign, including its end hold.
 * A sentence rule supplies the same channels to all items in that sentence.
 * Shared cached clip/keyframes remain untouched.
 */
export function mergeNmm(clip: SignClip, nmm?: NonManualMarkers, rules: string[] = []): SignClip {
  const values = parseNmm(nmm ?? {});
  if (!Object.keys(values).length) return clip;
  if (values.head && rules.includes("negation_nmm_pending_review")) {
    // Explicit demo-rule animation, never inferred from a gloss or from head yaw alone.
    // Existing numeric yaw is the amplitude; timing/scope need signer review.
    const merged = adaptClip(mergeNmm(clip, values));
    const original = new Map(merged.keys.map(key => [key.t, key]));
    const times = [...new Set([...original.keys(), ...Array.from({ length: 17 }, (_, i) => i / 16)])].sort((a, b) => a - b);
    const keys: KeyframeV2[] = times.map(t => {
      return { ...original.get(t), t,
        // Only head is resampled; sparse manual and face tracks retain their authored keys.
        head: [values.head![0], values.head![1] * Math.sin(4 * Math.PI * t), values.head![2]],
      };
    });
    return { ...merged, keys };
  }
  const channels = {
    ...(values.brow != null ? { brow: values.brow } : {}),
    ...(values.head != null ? { head: values.head } : {}),
    ...(values.mouth != null ? { mouth: values.mouth } : {}),
  };
  if (values.gaze || values.mouth_shape || clip.version === 2) {
    const adapted = adaptClip(clip);
    return { ...adapted, keys: adapted.keys.map(key => ({ ...key, ...channels, face: { ...key.face,
      ...(values.mouth != null ? { mouth_open: values.mouth } : {}),
      ...(values.brow != null ? { brow_inner_up: Math.max(0, values.brow), brow_down_left: Math.max(0, -values.brow), brow_down_right: Math.max(0, -values.brow) } : {}),
      ...(values.gaze ? { gaze_x: values.gaze[0], gaze_y: values.gaze[1] } : {}),
      ...Object.fromEntries(Object.entries(values.mouth_shape ?? {}).filter(([,v]) => v != null).map(([k,v]) => [`mouth_${k}`, v])),
    } })) };
  }
  return { ...clip, keys: clip.keys.map((key) => ({ ...key, ...channels })) } as SignClip;
}
