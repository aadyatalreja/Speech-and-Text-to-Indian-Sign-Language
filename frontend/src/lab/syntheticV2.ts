/** SYNTHETIC numeric fixtures, imported by the lab only. Never sign definitions. */
import type { SignClipV2, FingerJoints } from "../avatar/types";
import { eulerYXZToQuat } from "../avatar/pose";
const joints = (angle: number) => Array.from({ length: 15 }, () => eulerYXZToQuat([angle, 0, 0])) as FingerJoints;
export const SYNTHETIC_V2: SignClipV2[] = [
  { version: 2, id: "synthetic-joints", gloss: "SYNTHETIC_JOINTS", kind: "demo", notes: "SYNTHETIC software fixture; not ISL", keys: [
    { t: 0, R: { p: [-0.4, 0, 0.4], wrist: [0,0,0,1], fingers: joints(0) } },
    { t: 1, R: { fingers: joints(70) } },
  ] },
  { version: 2, id: "synthetic-face", gloss: "SYNTHETIC_FACE", kind: "demo", notes: "SYNTHETIC software fixture; not ISL", keys: [
    { t: 0, face: { mouth_open: 0, mouth_wide: 1, mouth_round: 0, eye_blink: 0, gaze_x: -1, gaze_y: -1, brow_inner_up: 0, brow_down_left: 1, brow_down_right: 0 } },
    { t: 1, face: { mouth_open: 1, mouth_wide: 0, mouth_round: 1, eye_blink: 1, gaze_x: 1, gaze_y: 1, brow_inner_up: 1, brow_down_left: 0, brow_down_right: 1 } },
  ] },
  { version: 2, id: "synthetic-torso", gloss: "SYNTHETIC_TORSO", kind: "demo", notes: "SYNTHETIC software fixture; not ISL", keys: [
    { t: 0, torso: { lean_x: -15, lean_z: -10, shoulder_raise_left: 0, shoulder_raise_right: 0.2 } },
    { t: 1, torso: { lean_x: 15, lean_z: 10, shoulder_raise_left: 0.2, shoulder_raise_right: 0 } },
  ] },
];
