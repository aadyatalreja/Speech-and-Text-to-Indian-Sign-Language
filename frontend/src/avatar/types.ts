/**
 * Sign clip format (v1)
 * ---------------------
 * Coordinates are in "viewer space", measured in shoulder-widths with the origin at the
 * mid-point between the shoulders:  +x = viewer's right, +y = up, +z = towards the viewer.
 * The signer's RIGHT hand therefore lives at negative x (it appears on the viewer's left),
 * exactly like a real signer facing you.
 *
 * Hand orientation: neutral = fingers up (+y), palm facing the viewer (+z).
 * `rot` is [pitch(x), yaw(y), roll(z)] in degrees, Euler order YXZ (roll applied first).
 *   pitch +  → fingers tilt towards the viewer      yaw + → palm normal turns towards +x
 *   roll  180 → fingers point down
 * `q` (quaternion x,y,z,w) can be given instead of `rot` (lossless, used by the dataset converter).
 *
 * Handshape: curls are [thumb, index, middle, ring, pinky], 0 = straight, 1 = fully curled.
 */
export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];
export type Curls = [number, number, number, number, number];

export interface HandSpec {
  p: Vec3;
  rot?: Vec3;
  q?: Quat;
  /** preset name (see handshapes.ts) or explicit curls */
  shape?: string | Curls;
  /** finger fan, 0 = together, 1 = wide, negative = crossed */
  spread?: number;
  /** thumb swing away from the palm, 0..1 */
  thumbOut?: number;
}

export interface Keyframe {
  /** normalised time inside the sign, 0..1 */
  t: number;
  /** signer's right hand. null = explicitly return to rest. Omitted = keep previous value. */
  R?: HandSpec | null;
  L?: HandSpec | null;
  /** [pitch, yaw, roll] degrees */
  head?: Vec3;
  /** eyebrows: -1 (frown) .. 1 (raised) */
  brow?: number;
  /** mouth opening 0..1 */
  mouth?: number;
}

export type ClipKind = "demo" | "dataset" | "fingerspell";

export interface SignClip {
  version: 1;
  id: string;
  gloss: string;
  kind: ClipKind;
  keys: Keyframe[];
  /** free text: source, licence, signer, review status */
  notes?: string;
}

/** Fully resolved state of one hand at one instant. */
export interface HandState {
  p: Vec3;
  q: Quat;
  c: Curls;
  spread: number;
  thumbOut: number;
}

export interface AvatarPose {
  R: HandState;
  L: HandState;
  head: Vec3;
  brow: number;
  mouth: number;
}
