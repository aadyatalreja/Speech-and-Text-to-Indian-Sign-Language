import type { Curls } from "./types";

/** Reusable handshape presets: [thumb, index, middle, ring, pinky], 0 straight … 1 curled. */
export const HANDSHAPES: Record<string, Curls> = {
  flat: [0.1, 0, 0, 0, 0],
  open: [0, 0, 0, 0, 0],
  fist: [0.7, 1, 1, 1, 1],
  point: [0.8, 0, 1, 1, 1],
  two: [0.8, 0, 0, 1, 1],
  three: [0.1, 0, 0, 0, 1],
  four: [0.9, 0, 0, 0, 0],
  claw: [0.5, 0.55, 0.55, 0.55, 0.55],
  cee: [0.35, 0.45, 0.45, 0.45, 0.45],
  oh: [0.6, 0.6, 0.6, 0.6, 0.6],
  flatO: [0.65, 0.7, 0.7, 0.7, 0.7],
  ell: [0, 0, 1, 1, 1],
  why: [0, 1, 1, 1, 0],
  thumbUp: [0, 1, 1, 1, 1],
  pinkyUp: [0.8, 1, 1, 1, 0],
  okay: [0.55, 0.55, 0, 0, 0],
  hook: [0.8, 0.6, 1, 1, 1],
  relaxed: [0.25, 0.3, 0.35, 0.4, 0.45],
};

export const REST_SHAPE: Curls = HANDSHAPES.relaxed;
