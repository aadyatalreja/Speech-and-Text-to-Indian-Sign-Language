import type { HandSpec, Keyframe, SignClip, Vec3 } from "./types";

/**
 * DEMO motions, hand-authored to exercise the engine (pointing, two-handed, head/brow, repeated
 * movement). They are rough approximations and are NOT verified ISL. Real signs should come from a
 * dataset or a native signer through the clip converter (backend/tools/mediapipe_to_clip.py).
 */
const NOTE = "Hand-authored demo motion for engine testing. Not verified ISL.";

const h = (p: Vec3, rot: Vec3, shape: HandSpec["shape"], extra: Partial<HandSpec> = {}): HandSpec => ({ p, rot, shape, ...extra });
const clip = (gloss: string, keys: Keyframe[]): SignClip => ({ version: 1, id: gloss.toLowerCase(), gloss, kind: "demo", keys, notes: NOTE });

// recurring orientations
const UP_PALM_FWD: Vec3 = [0, 0, 0];
const UP_PALM_BACK: Vec3 = [0, 180, 0];        // fingers up, palm towards the signer
const FWD_PALM_UP: Vec3 = [-90, 0, 180];       // fingers forward, palm up
const FWD_PALM_DOWN: Vec3 = [90, 0, 0];        // fingers forward, palm down

// Wrist positions assume the hand is drawn 1.3x: a flat hand is ~0.72 shoulder-widths from wrist to fingertip.
const selfPoint: SignClip[] = ["I", "ME"].map((g) => clip(g, [
  { t: 0, R: h([-0.55, -0.6, 1.0], [-60, 10, 0], "point") },
  { t: 0.45, R: h([-0.12, -0.3, 0.95], [-70, 15, 0], "point") },
  { t: 1, R: h([-0.12, -0.3, 0.95], [-70, 15, 0], "point") },
]));

export const DEMO_SIGNS: SignClip[] = [
  ...selfPoint,
  clip("YOU", [
    { t: 0, R: h([-0.35, -0.2, 0.35], FWD_PALM_DOWN, "point") },
    { t: 0.5, R: h([-0.35, -0.2, 0.7], FWD_PALM_DOWN, "point") },
    { t: 1, R: h([-0.35, -0.2, 0.7], FWD_PALM_DOWN, "point") },
  ]),
  clip("MY", [
    { t: 0, R: h([-0.4, -0.35, 0.75], UP_PALM_BACK, "flat") },
    { t: 0.4, R: h([-0.1, -0.68, 0.34], UP_PALM_BACK, "flat") },
    { t: 1, R: h([-0.1, -0.68, 0.34], UP_PALM_BACK, "flat") },
  ]),
  clip("YOUR", [
    { t: 0, R: h([-0.5, -0.45, 0.4], UP_PALM_FWD, "flat") },
    { t: 0.55, R: h([-0.5, -0.35, 0.8], UP_PALM_FWD, "flat") },
    { t: 1, R: h([-0.5, -0.35, 0.8], UP_PALM_FWD, "flat") },
  ]),
  clip("HELLO", [
    { t: 0, R: h([-0.4, 0.1, 0.32], [10, 0, -10], "flat") },
    { t: 0.55, R: h([-0.4, 0.1, 0.32], [10, 0, -10], "flat") },
    { t: 1, R: h([-0.75, 0.2, 0.7], [25, 0, -35], "flat"), head: [-4, 0, 0], mouth: 0.1 },
  ]),
  clip("THANK_YOU", [
    { t: 0, R: h([-0.12, -0.42, 0.4], UP_PALM_BACK, "flat"), head: [4, 0, 0] },
    { t: 0.55, R: h([-0.12, -0.42, 0.4], UP_PALM_BACK, "flat"), head: [6, 0, 0] },
    { t: 1, R: h([-0.2, -0.6, 0.85], [-50, 180, 0], "flat"), head: [0, 0, 0] },
  ]),
  clip("GOOD", [
    { t: 0, R: h([-0.12, -0.42, 0.4], UP_PALM_BACK, "flat"), L: h([0.3, -0.75, 0.45], FWD_PALM_UP, "flat") },
    { t: 0.5, R: h([-0.12, -0.42, 0.4], UP_PALM_BACK, "flat"), L: h([0.3, -0.75, 0.45], FWD_PALM_UP, "flat") },
    { t: 1, R: h([0.15, -0.58, 0.6], FWD_PALM_UP, "flat"), L: h([0.3, -0.75, 0.45], FWD_PALM_UP, "flat"), head: [3, 0, 0] },
  ]),
  clip("GO", [
    { t: 0, R: h([-0.35, -0.4, 0.4], [30, 0, 0], "point") },
    { t: 1, R: h([-0.35, -0.2, 1.0], [75, 0, 0], "point") },
  ]),
  clip("COME", [
    { t: 0, R: h([-0.35, -0.2, 1.0], [75, 0, 0], "point") },
    { t: 1, R: h([-0.35, -0.45, 0.5], [20, 0, 0], "point") },
  ]),
  clip("EAT", [
    { t: 0, R: h([-0.1, -0.3, 0.75], UP_PALM_BACK, "flatO") },
    { t: 0.25, R: h([-0.06, -0.2, 0.4], UP_PALM_BACK, "flatO"), mouth: 0.4 },
    { t: 0.5, R: h([-0.1, -0.3, 0.65], UP_PALM_BACK, "flatO"), mouth: 0 },
    { t: 0.75, R: h([-0.06, -0.2, 0.4], UP_PALM_BACK, "flatO"), mouth: 0.4 },
    { t: 1, R: h([-0.1, -0.3, 0.65], UP_PALM_BACK, "flatO"), mouth: 0 },
  ]),
  clip("DRINK", [
    { t: 0, R: h([-0.2, -0.5, 0.65], [0, 30, 0], "cee") },
    { t: 0.5, R: h([-0.1, -0.3, 0.5], [-25, 30, 0], "cee"), head: [-8, 0, 0], mouth: 0.3 },
    { t: 1, R: h([-0.2, -0.5, 0.65], [0, 30, 0], "cee"), head: [0, 0, 0] },
  ]),
  clip("YES", [
    { t: 0, R: h([-0.35, -0.35, 0.55], [0, 0, 0], "fist"), head: [0, 0, 0] },
    { t: 0.25, R: h([-0.35, -0.35, 0.55], [-30, 0, 0], "fist"), head: [10, 0, 0] },
    { t: 0.5, R: h([-0.35, -0.35, 0.55], [0, 0, 0], "fist"), head: [0, 0, 0] },
    { t: 0.75, R: h([-0.35, -0.35, 0.55], [-30, 0, 0], "fist"), head: [10, 0, 0] },
    { t: 1, R: h([-0.35, -0.35, 0.55], [0, 0, 0], "fist"), head: [0, 0, 0] },
  ]),
  clip("NO", [
    { t: 0, R: h([-0.4, -0.3, 0.55], [0, 0, 0], "two"), head: [0, 0, 0] },
    { t: 0.3, R: h([-0.4, -0.3, 0.55], [0, 0, 0], "flatO"), head: [0, -14, 0] },
    { t: 0.55, R: h([-0.4, -0.3, 0.55], [0, 0, 0], "two"), head: [0, 14, 0] },
    { t: 0.8, R: h([-0.4, -0.3, 0.55], [0, 0, 0], "flatO"), head: [0, -14, 0] },
    { t: 1, R: h([-0.4, -0.3, 0.55], [0, 0, 0], "two"), head: [0, 0, 0] },
  ]),
  clip("HELP", [
    { t: 0, R: h([0.18, -0.68, 0.6], [0, 0, 0], "thumbUp"), L: h([0.2, -0.85, 0.38], FWD_PALM_UP, "flat") },
    { t: 0.5, R: h([0.18, -0.8, 0.6], [0, 0, 0], "thumbUp"), L: h([0.2, -0.97, 0.38], FWD_PALM_UP, "flat") },
    { t: 1, R: h([0.18, -0.4, 0.6], [0, 0, 0], "thumbUp"), L: h([0.2, -0.57, 0.38], FWD_PALM_UP, "flat") },
  ]),
  clip("NOT", [
    { t: 0, R: h([-0.1, -0.35, 0.65], FWD_PALM_DOWN, "flat"), head: [0, 0, 0] },
    { t: 0.6, R: h([-0.65, -0.35, 0.65], FWD_PALM_DOWN, "flat"), head: [0, 12, 0] },
    { t: 1, R: h([-0.65, -0.35, 0.65], FWD_PALM_DOWN, "flat"), head: [0, -10, 0] },
  ]),
  clip("WHAT", [
    { t: 0, R: h([-0.55, -0.6, 0.5], FWD_PALM_UP, "open", { spread: 0.8 }), L: h([0.55, -0.6, 0.5], FWD_PALM_UP, "open", { spread: 0.8 }), brow: 0.9, head: [0, 0, 6] },
    { t: 0.5, R: h([-0.75, -0.5, 0.55], FWD_PALM_UP, "open", { spread: 0.8 }), L: h([0.75, -0.5, 0.55], FWD_PALM_UP, "open", { spread: 0.8 }), brow: 0.9, head: [0, 0, 6] },
    { t: 1, R: h([-0.55, -0.6, 0.5], FWD_PALM_UP, "open", { spread: 0.8 }), L: h([0.55, -0.6, 0.5], FWD_PALM_UP, "open", { spread: 0.8 }), brow: 0.9, head: [0, 0, 6] },
  ]),
  clip("WHERE", [
    { t: 0, R: h([-0.5, -0.4, 0.55], [0, 0, 0], "point"), brow: 0.8 },
    { t: 0.3, R: h([-0.5, -0.4, 0.55], [0, 0, -25], "point"), brow: 0.8 },
    { t: 0.6, R: h([-0.5, -0.4, 0.55], [0, 0, 25], "point"), brow: 0.8 },
    { t: 1, R: h([-0.5, -0.4, 0.55], [0, 0, 0], "point"), brow: 0.8 },
  ]),
  clip("PLEASE", [
    { t: 0, R: h([-0.1, -0.7, 0.36], UP_PALM_BACK, "flat") },
    { t: 0.33, R: h([-0.05, -0.6, 0.36], UP_PALM_BACK, "flat") },
    { t: 0.66, R: h([-0.2, -0.82, 0.36], UP_PALM_BACK, "flat") },
    { t: 1, R: h([-0.1, -0.7, 0.36], UP_PALM_BACK, "flat") },
  ]),
];
