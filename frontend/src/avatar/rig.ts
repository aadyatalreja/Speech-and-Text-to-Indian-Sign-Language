import * as THREE from "three";
import { restPose } from "./pose";
import type { AvatarPose, HandState } from "./types";

/**
 * Procedural signer built from primitives, so the demo works offline with no model file.
 * Units are shoulder-widths (see types.ts). Arms are solved with analytic two-bone IK so ANY
 * wrist position in a clip is reachable; hands have 5 articulated fingers; the head carries
 * brows and mouth for non-manual markers.
 */

const UPPER = 0.8, FORE = 0.7;
const SHOULDER_X = 0.5;
const FINGER_X = [0.09, 0.03, -0.03, -0.09]; // index..pinky, measured from the thumb side (before mirroring)
const FINGER_LEN = [[0.13, 0.08, 0.065], [0.14, 0.085, 0.07], [0.13, 0.08, 0.065], [0.105, 0.062, 0.055]];
const FINGER_R = 0.036;
const PALM_H = 0.27;
const MCP = 80 * (Math.PI / 180), PIP = 100 * (Math.PI / 180), DIP = 60 * (Math.PI / 180);
const DEG = Math.PI / 180;
/** Hands are drawn 1.3x life-size: hands carry the language, so they must read at a glance. */
const HAND_SCALE = 1.3;

export interface RigColors { skin: string; shirt: string; hair: string; accent: string }

interface HandRig {
  root: THREE.Group;
  fingers: THREE.Group[][];   // [finger][joint]
  fingerBase: THREE.Group[];
  thumbBase: THREE.Group;
  thumbJoints: THREE.Group[];
  side: 1 | -1;               // +1 for the signer's right hand (thumb on +x)
}

const capsule = (r: number, len: number, mat: THREE.Material) => {
  const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(len - r, 0.001), 6, 12), mat); // slightly long: segments overlap at joints
  m.castShadow = false;
  return m;
};

export class AvatarRig {
  readonly group = new THREE.Group();
  private hands: { R: HandRig; L: HandRig };
  private arms: Record<"R" | "L", { upper: THREE.Mesh; fore: THREE.Mesh; elbow: THREE.Mesh }>;
  private head = new THREE.Group();
  private brows: THREE.Mesh[] = [];
  private mouth: THREE.Mesh;
  private torso: THREE.Mesh;
  private mats: Record<string, THREE.MeshStandardMaterial>;
  private tmp = { dir: new THREE.Vector3(), a: new THREE.Vector3(), b: new THREE.Vector3(), q: new THREE.Quaternion(), up: new THREE.Vector3(0, 1, 0) };

  constructor(colors: RigColors) {
    const mk = (c: string, rough = 0.65) => new THREE.MeshStandardMaterial({ color: c, roughness: rough, metalness: 0.02 });
    this.mats = { skin: mk(colors.skin, 0.55), shirt: mk(colors.shirt, 0.8), hair: mk(colors.hair, 0.9), dark: mk("#1c1c26", 0.4), accent: mk(colors.accent, 0.6), mouth: mk("#7a2a35", 0.6) };

    // torso, neck, shoulders
    this.torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 0.95, 8, 20), this.mats.shirt);
    this.torso.scale.set(1.2, 1, 0.58);
    this.torso.position.set(0, -0.82, 0);
    this.group.add(this.torso);
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 0.28, 16), this.mats.skin);
    neck.position.set(0, 0.12, 0);
    this.group.add(neck);
    for (const s of [-1, 1]) {
      const sh = new THREE.Mesh(new THREE.SphereGeometry(0.17, 16, 12), this.mats.shirt);
      sh.position.set(s * SHOULDER_X, 0, 0);
      this.group.add(sh);
    }

    // head (pivot at neck top)
    this.head.position.set(0, 0.22, 0);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.29, 28, 20), this.mats.skin);
    skull.scale.set(0.92, 1.12, 0.98);
    skull.position.set(0, 0.36, 0);
    const hair = new THREE.Mesh(new THREE.SphereGeometry(0.305, 28, 20, 0, Math.PI * 2, 0, Math.PI * 0.42), this.mats.hair);
    hair.scale.set(0.93, 1.13, 1.0);
    hair.position.set(0, 0.37, -0.015);
    hair.rotation.x = -0.38;
    this.head.add(skull, hair);
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.032, 12, 10), this.mats.dark);
      eye.position.set(s * 0.105, 0.4, 0.265);
      const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.012, 0.09, 4, 8), this.mats.hair);
      brow.rotation.z = Math.PI / 2;
      brow.position.set(s * 0.105, 0.48, 0.275);
      this.brows.push(brow);
      const ear = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), this.mats.skin);
      ear.scale.set(0.5, 1, 0.8);
      ear.position.set(s * 0.265, 0.34, 0);
      this.head.add(eye, brow, ear);
    }
    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.07, 10), this.mats.skin);
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 0.32, 0.3);
    this.mouth = new THREE.Mesh(new THREE.SphereGeometry(0.05, 14, 10), this.mats.mouth);
    this.mouth.scale.set(1.2, 0.35, 0.4);
    this.mouth.position.set(0, 0.2, 0.27);
    this.head.add(nose, this.mouth);
    this.group.add(this.head);

    // arms
    const arm = () => ({
      upper: capsule(0.085, UPPER + 0.1, this.mats.shirt),
      fore: capsule(0.065, FORE + 0.05, this.mats.skin),
      elbow: new THREE.Mesh(new THREE.SphereGeometry(0.085, 12, 10), this.mats.shirt),
    });
    this.arms = { R: arm(), L: arm() };
    for (const a of Object.values(this.arms)) this.group.add(a.upper, a.fore, a.elbow);

    this.hands = { R: this.buildHand(1), L: this.buildHand(-1) };
    this.group.add(this.hands.R.root, this.hands.L.root);
    this.applyPose(restPose());
  }

  private buildHand(side: 1 | -1): HandRig {
    const root = new THREE.Group();
    const palm = new THREE.Mesh(new THREE.CapsuleGeometry(0.1, 0.09, 6, 14), this.mats.skin);
    palm.scale.set(1.35, 1, 0.5);
    palm.position.set(0, PALM_H / 2 + 0.01, 0);
    root.add(palm);
    const cuff = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.05, 14), this.mats.accent);
    cuff.position.set(0, -0.02, 0);
    root.add(cuff);

    const fingers: THREE.Group[][] = [], fingerBase: THREE.Group[] = [];
    FINGER_LEN.forEach((segs, i) => {
      const base = new THREE.Group();
      base.position.set(side * FINGER_X[i], PALM_H, 0);
      let parent: THREE.Object3D = base;
      const joints: THREE.Group[] = [];
      segs.forEach((len, j) => {
        const joint = new THREE.Group();
        if (j > 0) joint.position.set(0, segs[j - 1], 0);
        const seg = capsule(FINGER_R * (1 - j * 0.1), len, this.mats.skin);
        seg.position.set(0, len / 2, 0);
        joint.add(seg);
        parent.add(joint);
        parent = joint;
        joints.push(joint);
      });
      root.add(base);
      fingers.push(joints);
      fingerBase.push(base);
    });

    const thumbBase = new THREE.Group();
    thumbBase.position.set(side * 0.1, 0.05, 0.015);
    const tl = [0.12, 0.085, 0.07];
    const thumbJoints: THREE.Group[] = [];
    let parent: THREE.Object3D = thumbBase;
    tl.forEach((len, j) => {
      const joint = new THREE.Group();
      if (j > 0) joint.position.set(0, tl[j - 1], 0);
      const seg = capsule(0.036 * (1 - j * 0.08), len, this.mats.skin);
      seg.position.set(0, len / 2, 0);
      joint.add(seg);
      parent.add(joint);
      parent = joint;
      thumbJoints.push(joint);
    });
    root.add(thumbBase);
    return { root, fingers, fingerBase, thumbBase, thumbJoints, side };
  }

  /* ---------- posing ---------- */

  private poseHand(h: HandRig, st: HandState) {
    h.root.position.set(st.p[0], st.p[1], st.p[2]);
    h.root.scale.setScalar(HAND_SCALE);
    h.root.quaternion.set(st.q[0], st.q[1], st.q[2], st.q[3]);
    for (let i = 0; i < 4; i++) {
      const c = Math.min(1, Math.max(0, st.c[i + 1]));
      const [mcp, pip, dip] = h.fingers[i];
      mcp.rotation.x = c * MCP; pip.rotation.x = c * PIP; dip.rotation.x = c * DIP;
      // fan: index (nearest the thumb) tilts toward the thumb side, pinky away
      h.fingerBase[i].rotation.z = -h.side * (1.5 - i) * st.spread * 0.2;
    }
    const tc = Math.min(1, Math.max(0, st.c[0]));
    const out = Math.min(1, Math.max(0, st.thumbOut));
    // abduction swings the thumb away from the palm; curl folds it across the palm
    h.thumbBase.rotation.z = -h.side * ((8 + 52 * out) * DEG * (1 - 0.7 * tc));
    h.thumbBase.rotation.y = h.side * (-0.5 * tc);
    h.thumbBase.rotation.x = tc * 0.55 + (1 - out) * 0.1;
    h.thumbJoints[0].rotation.x = tc * 0.5;
    h.thumbJoints[1].rotation.x = tc * 0.75;
    h.thumbJoints[2].rotation.x = tc * 0.6;
  }

  /** Two-bone IK from shoulder to wrist; returns the elbow. Elbow is pushed down/out/back. */
  private solveArm(side: "R" | "L", wrist: THREE.Vector3) {
    const { a: S, b: pole, dir, q, up } = this.tmp;
    const sx = side === "R" ? -SHOULDER_X : SHOULDER_X;
    S.set(sx, 0, 0);
    dir.copy(wrist).sub(S);
    let d = dir.length();
    const dMax = UPPER + FORE - 1e-3, dMin = Math.abs(UPPER - FORE) + 1e-3;
    d = Math.min(dMax, Math.max(dMin, d));
    if (dir.lengthSq() < 1e-8) dir.set(0, -1, 0);
    dir.normalize();
    const wristC = S.clone().addScaledVector(dir, d);
    pole.set(Math.sign(sx) * 0.45, -1, -0.35);
    pole.addScaledVector(dir, -pole.dot(dir));
    if (pole.lengthSq() < 1e-6) pole.set(0, 0, -1);
    pole.normalize();
    const a = (UPPER * UPPER - FORE * FORE + d * d) / (2 * d);
    const h = Math.sqrt(Math.max(UPPER * UPPER - a * a, 0));
    const elbow = S.clone().addScaledVector(dir, a).addScaledVector(pole, h);

    const arm = this.arms[side];
    const place = (m: THREE.Mesh, from: THREE.Vector3, to: THREE.Vector3) => {
      const v = to.clone().sub(from);
      m.position.copy(from).addScaledVector(v, 0.5);
      q.setFromUnitVectors(up, v.normalize());
      m.quaternion.copy(q);
    };
    place(arm.upper, S.clone(), elbow);
    place(arm.fore, elbow, wristC);
    arm.elbow.position.copy(elbow);
    return wristC;
  }

  applyPose(p: AvatarPose) {
    for (const side of ["R", "L"] as const) {
      const st = p[side];
      const w = this.solveArm(side, new THREE.Vector3(st.p[0], st.p[1], st.p[2]));
      const hand = this.hands[side];
      this.poseHand(hand, st);
      hand.root.position.copy(w); // wrist snaps to the reachable point
    }
    this.head.rotation.set(p.head[0] * DEG, p.head[1] * DEG, p.head[2] * DEG, "YXZ");
    this.brows.forEach((b, i) => {
      b.position.y = 0.48 + 0.045 * p.brow;
      b.rotation.z = Math.PI / 2 + (i === 0 ? 1 : -1) * -0.18 * Math.min(0, p.brow);
    });
    this.mouth.scale.y = 0.35 + 1.4 * p.mouth;
  }

  /** Idle motion layered on top of any pose (breathing). */
  idle(time: number) {
    const s = 1 + Math.sin(time * 1.6) * 0.008;
    this.torso.scale.set(1.2 * s, 1, 0.58 * s);
  }

  setColors(c: RigColors) {
    this.mats.skin.color.set(c.skin); this.mats.shirt.color.set(c.shirt);
    this.mats.hair.color.set(c.hair); this.mats.accent.color.set(c.accent);
  }

  dispose() {
    this.group.traverse((o) => { const m = o as THREE.Mesh; m.geometry?.dispose?.(); });
    Object.values(this.mats).forEach((m) => m.dispose());
  }
}
