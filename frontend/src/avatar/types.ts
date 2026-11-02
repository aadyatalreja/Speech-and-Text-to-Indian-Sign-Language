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

export interface SignClipV1 {
  version: 1;
  id: string;
  gloss: string;
  kind: ClipKind;
  keys: Keyframe[];
  /** free text: source, licence, signer, review status */
  notes?: string;
  duration?: number;
  source?: string | null;
  licence?: string | null;
  signer?: string | null;
  review_status?: "unverified" | "in_review" | "verified";
  spelling?: {
    duration: number;
    missing: string[];
    unverified: string[];
    textOnly: string[];
    assets: { character: string; source: string; licence: string; signer: string; review_status: "unverified" | "in_review" | "verified" }[];
  };
}

/** Fully resolved state of one hand at one instant. */
export interface HandState {
  p: Vec3;
  q: Quat;
  c: Curls;
  spread: number;
  thumbOut: number;
  fingers?: FingerJoints;
}

export interface AvatarPose {
  R: HandState;
  L: HandState;
  head: Vec3;
  brow: number;
  mouth: number;
  face?: FaceChannels;
  torso?: TorsoChannels;
}

/** Local rotations, thumb/index/middle/ring/pinky, proximal to distal (3 each).
 * x,y,z,w unit quaternions. Neutral bones point +Y; +X flexes toward the palm.
 * Wrist rotation is absolute in clip space, as in v1 q.
 */
export type FingerJoints = [Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat, Quat];
export interface FaceChannels {
  mouth_open?: number; mouth_wide?: number; mouth_round?: number;
  brow_inner_up?: number; brow_down_left?: number; brow_down_right?: number;
  eye_blink?: number; gaze_x?: number; gaze_y?: number;
}
/** Lean angles in degrees (-30..30); shoulder raises in shoulder widths (0..0.3). */
export interface TorsoChannels { lean_x?: number; lean_z?: number; shoulder_raise_left?: number; shoulder_raise_right?: number }
export interface HandSpecV2 extends Partial<HandSpec> { wrist?: Quat; fingers?: FingerJoints }
export interface KeyframeV2 extends Omit<Keyframe, "R" | "L"> {
  R?: HandSpecV2 | null; L?: HandSpecV2 | null;
  face?: FaceChannels; torso?: TorsoChannels;
}
export interface SignClipV2 extends Omit<SignClipV1, "version" | "keys"> { version: 2; keys: KeyframeV2[] }
export type SignClip = SignClipV1 | SignClipV2;
