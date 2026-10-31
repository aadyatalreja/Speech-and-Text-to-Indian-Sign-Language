import type { NonManualMarkers } from "../types/translation";
import type { SignClip, Vec3 } from "./types";

/** Rig channel validation, not a linguistic rule or sign definition. */
export function parseNmm(raw: unknown): NonManualMarkers {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("NMM must be an object");
  const value = raw as Record<string, unknown>;
  if (Object.keys(value).some((key) => !["brow", "head", "mouth"].includes(key))) throw new Error("Unknown NMM channel");
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
  return result;
}

/** Override only configured channels across the sign, including its end hold.
 * A sentence rule supplies the same channels to all items in that sentence.
 * Shared cached clip/keyframes remain untouched.
 */
export function mergeNmm(clip: SignClip, nmm?: NonManualMarkers): SignClip {
  const values = parseNmm(nmm ?? {});
  if (!Object.keys(values).length) return clip;
  const channels = {
    ...(values.brow != null ? { brow: values.brow } : {}),
    ...(values.head != null ? { head: values.head } : {}),
    ...(values.mouth != null ? { mouth: values.mouth } : {}),
  };
  return { ...clip, keys: clip.keys.map((key) => ({ ...key, ...channels })) };
}
