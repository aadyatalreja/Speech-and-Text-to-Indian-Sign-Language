import type { HandSpec, Keyframe } from "./types";

type Hands = Pick<Keyframe, "L" | "R">;
const hand = (
  x: number, y: number, shape: HandSpec["shape"],
  roll = 0, yaw = 0, spread = 0, thumbOut = 0.25, z = 0.65,
): HandSpec => ({ p: [x, y, z], rot: [0, yaw, roll], shape, spread, thumbOut });

const digit = (shape: HandSpec["shape"], spread = 0, thumbOut = 0.25): Hands =>
  ({ R: hand(-0.42, -0.32, shape, 0, 0, spread, thumbOut), L: null });
const bar = (y = -0.27) => hand(0.45, y, "flat", 90, 0, 0.1);
const point = (x: number, y: number, roll = 0, z = 0.71) =>
  hand(x, y, "point", roll, 0, 0, 0.25, z);

// Wrist placements and handshapes interpreted from the supplied front-view charts.
// Depth, contact and inter-character motion are approximations for the avatar rig.
export const CHARACTER_POSES: Record<string, Hands> = {
  A: { R: hand(-0.38, -0.3, "fist", -85, 0, 0, 0.55), L: hand(0.38, -0.3, "fist", 85, 0, 0, 0.55) },
  B: { R: hand(-0.34, -0.47, "oh", -35), L: hand(0.34, -0.47, "oh", 35) },
  C: digit("cee", 0, 0.65),
  D: { R: point(-0.26, -0.62), L: hand(0.37, -0.2, "cee", 90, 0, 0, 0.65) },
  E: { R: hand(-0.45, -0.28, "ell", -75, 0, 0, 0.9), L: point(0.24, -0.55, 25) },
  F: { R: hand(-0.35, -0.31, "fist", -75), L: hand(0.16, -0.53, "two", 23, 0, 0.1, 0.25, 0.75) },
  G: { R: hand(-0.31, -0.17, "fist", -90), L: hand(0.24, -0.46, "fist", 90) },
  H: { R: hand(-0.4, -0.28, "flat", -90, 0, 0.15, 0.25, 0.57), L: hand(0.12, -0.54, "flat", 12, 0, 0.25) },
  I: { R: point(-0.08, -0.64), L: hand(0.17, -0.14, "fist", 145, 0, 0, 0.25, 0.58) },
  J: { R: point(0.09, -0.64), L: hand(-0.4, -0.25, "ell", -80, 0, 0, 0.85) },
  K: { R: hand(-0.16, -0.62, "two", -10, 0, 0.45), L: hand(0.29, -0.12, "hook", 140) },
  L: digit("ell", 0, 1),
  M: { R: hand(0.02, -0.69, [0.85, 0, 0, 0, 1], 0, 0, 0.05, 0.25, 0.77), L: bar() },
  N: { R: hand(0.02, -0.69, "two", 0, 0, 0.07, 0.25, 0.77), L: bar() },
  O: digit("oh", 0, 0.72),
  P: { R: point(-0.18, -0.63), L: hand(0.27, -0.33, "oh", 70, 0, 0, 0.65) },
  Q: { R: hand(-0.28, -0.31, "oh", -20, 0, 0, 0.7), L: point(0.24, -0.62, 36) },
  R: { R: hand(-0.05, -0.65, "hook", 10, 0, 0, 0.25, 0.78), L: bar() },
  S: { R: hand(-0.12, -0.57, "pinkyUp", -8), L: hand(0.38, -0.2, "cee", 95) },
  T: { R: point(0.03, -0.72), L: hand(0.5, -0.18, "point", 90) },
  U: digit([0.85, 0, 1, 1, 0], 0.25),
  V: digit("two", 0.65),
  W: { R: hand(-0.28, -0.49, "flat", -42, 10, 0.08), L: hand(0.28, -0.49, "flat", 42, -10, 0.08, 0.25, 0.73) },
  X: { R: point(-0.4, -0.51, -48), L: point(0.4, -0.51, 48, 0.64) },
  Y: { R: point(-0.38, -0.46, -38), L: hand(0.15, -0.61, "why", 12, 0, 0.42) },
  Z: { R: hand(-0.3, -0.53, "flat", -45, 0, 0.1, 0.25, 0.73), L: hand(0.21, -0.57, "flat", 4, -42) },
  "0": digit("oh", 0, 0.62),
  "1": digit("point"),
  "2": digit("two", 0.65),
  "3": digit([0, 0, 0, 1, 1], 0.55, 1),
  "4": digit("four", 0.52),
  "5": digit("open", 0.75, 1),
  "6": digit([0.63, 0, 0, 0, 0.95], 0.42, 0.08),
  "7": digit([0.63, 0, 0, 0.95, 0], 0.42, 0.08),
  "8": digit([0.63, 0, 0.95, 0, 0], 0.42, 0.08),
  "9": digit("okay", 0.42, 0.08),
};
