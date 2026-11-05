import * as THREE from "three";
import { restPose, resolvedFace } from "./pose";
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
/** Display gains only, not linguistic amplitudes. PoseFollower smooths these inputs. */
export const EXPRESSION_STYLE = { browRaise: 0.085, browLower: 0.065, browSlope: 0.48, headGain: 1.2, gazeSquint: 0.10, browSquint: 0.22 };

export interface RigColors { skin: string; shirt: string; hair: string; accent: string }

import type { CharacterId } from "./characters";
export type { CharacterId } from "./characters";

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
  private eyes: THREE.Mesh[] = [];
  private lids: THREE.Mesh[] = [];
  private shoulders: THREE.Mesh[] = [];
  private shoulderRaise = { R: 0, L: 0 };
  private mouth: THREE.Mesh;
  private torso: THREE.Mesh;
  private mats: Record<string, THREE.MeshStandardMaterial>;
  /** Cosmetic extras only (long hair, lashes): same skeleton, so every pose is unchanged. */
  private femaleParts = new THREE.Group();
  /** Male look: smooth torso with integrated shoulders + short curly hair. */
  private maleParts = new THREE.Group();
  private maleTorso!: THREE.Mesh;
  /** Female look: orange top and skirt (same theme orange as the male shirt) with white flowers. Own materials so theme recolouring leaves it alone. */
  private fem = {
    shirt: new THREE.MeshStandardMaterial({ color: "#f4f3ef", roughness: 0.7 }),
    button: new THREE.MeshStandardMaterial({ color: "#9aa3ad", roughness: 0.4 }),
  };
  private femaleSkirt!: THREE.Mesh;
  private eyeWhites: THREE.Mesh[] = [];
  private nose!: THREE.Mesh;
  private femaleNose!: THREE.Mesh;
  private femaleShirtParts = new THREE.Group();
  private hairCap!: THREE.Mesh;
  private vneck!: THREE.Mesh;
  private blush = new THREE.MeshStandardMaterial({ color: "#e08a85", roughness: 0.9, transparent: true, opacity: 0.55 });
  private character: CharacterId = "arav";
  /** Anya's curls, Devi's straight hair + jewellery (head), Devi's saree drape, Dev's kurta details. */
  private anyaHair = new THREE.Group();
  private deviParts = new THREE.Group();
  private deviBody = new THREE.Group();
  private devParts = new THREE.Group();
  private ethnic = {
    saree: new THREE.MeshStandardMaterial({ color: "#c2185b", roughness: 0.55 }),
    blouse: new THREE.MeshStandardMaterial({ color: "#d4a22a", roughness: 0.5 }),
    gold: new THREE.MeshStandardMaterial({ color: "#e0b54a", roughness: 0.35, metalness: 0.4 }),
    kurta: new THREE.MeshStandardMaterial({ color: "#f1e4c4", roughness: 0.75 }),
    bindi: new THREE.MeshStandardMaterial({ color: "#b0122e", roughness: 0.5 }),
  };
  private skull!: THREE.Mesh;
  private neck!: THREE.Mesh;
  private torsoX = 1.2;
  /** Smooth lathe torso with sloped shoulders for the female look; arms attach at its shoulder line. */
  private femaleTorso!: THREE.Mesh;
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
    this.neck = neck;
    this.group.add(neck);
    for (const s of [-1, 1]) {
      const sh = new THREE.Mesh(new THREE.SphereGeometry(0.17, 16, 12), this.mats.shirt);
      sh.position.set(s * SHOULDER_X, 0, 0);
      this.shoulders.push(sh);
      this.group.add(sh);
    }

    // female torso: one smooth silhouette (neck -> sloped shoulders -> bust -> waist -> hip)
    const profile = new THREE.SplineCurve([
      new THREE.Vector2(0.0, 0.16), new THREE.Vector2(0.13, 0.15), new THREE.Vector2(0.3, 0.12),
      new THREE.Vector2(0.48, 0.08), new THREE.Vector2(0.57, 0.0), new THREE.Vector2(0.58, -0.12),
      new THREE.Vector2(0.5, -0.32),
      new THREE.Vector2(0.41, -0.55), new THREE.Vector2(0.35, -0.88), new THREE.Vector2(0.4, -1.25),
      new THREE.Vector2(0.42, -1.6), new THREE.Vector2(0.0, -1.72),
    ]).getPoints(64).map(v => new THREE.Vector2(Math.max(v.x, 0), v.y)).reverse(); // bottom-to-top => outward-facing normals
    const WAIST = -0.92;
    const cut = profile.findIndex(v => v.y >= WAIST);
    // flared skirt from the waist, same theme orange as the top and the male shirt
    const waistR = profile[cut].x;
    const skirt = new THREE.SplineCurve([
      new THREE.Vector2(0.0, -1.7), new THREE.Vector2(0.62, -1.68), new THREE.Vector2(0.56, -1.4),
      new THREE.Vector2(0.46, -1.12), new THREE.Vector2(waistR + 0.02, WAIST - 0.02), new THREE.Vector2(waistR, WAIST + 0.03),
    ]).getPoints(40).map(v => new THREE.Vector2(Math.max(v.x, 0), v.y));   // bottom-to-top => outward normals
    this.femaleSkirt = new THREE.Mesh(new THREE.LatheGeometry(skirt, 48), this.mats.shirt);
    this.femaleTorso = new THREE.Mesh(new THREE.LatheGeometry(profile.slice(cut), 40), this.mats.shirt);
    for (const m of [this.femaleTorso, this.femaleSkirt]) {
      m.scale.set(1, 1, 0.55);
      m.visible = false;
      this.group.add(m);
    }
    const maleProfile = new THREE.SplineCurve([
      new THREE.Vector2(0.0, 0.16), new THREE.Vector2(0.13, 0.15), new THREE.Vector2(0.3, 0.12),
      new THREE.Vector2(0.48, 0.08), new THREE.Vector2(0.58, 0.0), new THREE.Vector2(0.59, -0.12),
      new THREE.Vector2(0.55, -0.35), new THREE.Vector2(0.5, -0.65), new THREE.Vector2(0.47, -1.0),
      new THREE.Vector2(0.47, -1.4), new THREE.Vector2(0.45, -1.65), new THREE.Vector2(0.0, -1.72),
    ]).getPoints(64).map(v => new THREE.Vector2(Math.max(v.x, 0), v.y)).reverse();
    this.maleTorso = new THREE.Mesh(new THREE.LatheGeometry(maleProfile, 40), this.mats.shirt);
    this.maleTorso.scale.set(1, 1, 0.55);
    this.group.add(this.maleTorso);
    this.torso.visible = false;                       // old capsule torso replaced by the lathe torsos
    this.shoulders.forEach(sh => { sh.visible = false; });

    // open V-neck (skin) with a collar flap on each side, so the shirt clearly faces forward
    const tri = (pts: number[][], mat: THREE.Material) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(pts.flat(), 3));
      g.computeVertexNormals();
      return new THREE.Mesh(g, mat);
    };
    const open = new THREE.MeshStandardMaterial({ color: "#e3b393", roughness: 0.55, side: THREE.DoubleSide });
    this.vneck = tri([[-0.13, 0.12, 0.265], [0.13, 0.12, 0.265], [0, -0.18, 0.352]], open);
    this.femaleShirtParts.add(this.vneck);
    const collarMat = new THREE.MeshStandardMaterial({ color: "#fbfaf7", roughness: 0.6, side: THREE.DoubleSide });
    for (const s of [-1, 1]) {
      const flap = tri([[s * 0.12, 0.135, 0.275], [s * 0.28, 0.02, 0.34], [s * 0.012, -0.165, 0.362]], collarMat);
      this.femaleShirtParts.add(flap);
    }
    // button placket down the front of the shirt
    for (const [y, z] of [[-0.24, 0.3], [-0.42, 0.262], [-0.6, 0.225], [-0.78, 0.205]]) {
      const button = new THREE.Mesh(new THREE.SphereGeometry(0.016, 10, 8), this.fem.button);
      button.scale.set(1, 1, 0.5);
      button.position.set(0, y, z);
      this.femaleShirtParts.add(button);
    }
    // small flower print on the shirt front, each flower turned to lie on the shirt surface
    const radiusAt = (y: number) => {
      for (let i = 1; i < profile.length; i++) {
        const a = profile[i - 1], b = profile[i];
        if ((a.y - y) * (b.y - y) <= 0 && a.y !== b.y) return a.x + (b.x - a.x) * (y - a.y) / (b.y - a.y);
      }
      return 0.4;
    };
    const petalMats = [new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.6 })];
    const centre = new THREE.MeshStandardMaterial({ color: "#f2c94c", roughness: 0.5 });
    const spots: [number, number][] = [[-0.22, -0.14], [0.19, -0.22], [-0.13, -0.42], [0.27, -0.5], [-0.3, -0.66], [0.13, -0.72], [-0.05, -0.84], [0.32, -0.82]];
    spots.forEach(([x, y], i) => {
      const r = radiusAt(y);
      const z = 0.55 * Math.sqrt(Math.max(r * r - x * x, 0.0001));
      const flower = new THREE.Group();
      for (let k = 0; k < 5; k++) {
        const petal = new THREE.Mesh(new THREE.SphereGeometry(0.02, 10, 8), petalMats[i % petalMats.length]);
        const ang = (k / 5) * Math.PI * 2 + i;
        petal.scale.set(1, 1, 0.35);
        petal.position.set(Math.cos(ang) * 0.025, Math.sin(ang) * 0.025, 0);
        flower.add(petal);
      }
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.012, 8, 6), centre);
      dot.scale.set(1, 1, 0.5);
      dot.position.z = 0.004;
      flower.add(dot);
      const normal = new THREE.Vector3(x / 1, 0, z / 0.3025).normalize();   // ellipse normal (z scaled by 0.55)
      flower.position.set(x, y, z).addScaledVector(normal, 0.01);
      flower.lookAt(flower.position.clone().add(normal));
      this.femaleShirtParts.add(flower);
    });
    this.femaleShirtParts.visible = false;
    this.group.add(this.femaleShirtParts);

    // surface helpers: front of a lathe torso (z squashed by 0.55) and a ribbon that lies on it
    const radiusOf = (prof: THREE.Vector2[]) => (y: number) => {
      for (let i = 1; i < prof.length; i++) {
        const a = prof[i - 1], b = prof[i];
        if ((a.y - y) * (b.y - y) <= 0 && a.y !== b.y) return a.x + (b.x - a.x) * (y - a.y) / (b.y - a.y);
      }
      return 0.4;
    };
    const femaleR = radiusOf(profile), maleR = radiusOf(maleProfile);
    const surface = (r: (y: number) => number) => (x: number, y: number) => 0.55 * Math.sqrt(Math.max(r(y) ** 2 - x * x, 0));
    const ribbon = (path: [number, number][], width: number, lift: number, surf: (x: number, y: number) => number, mat: THREE.Material) => {
      const pts = new THREE.SplineCurve(path.map(([x, y]) => new THREE.Vector2(x, y))).getPoints(28);
      const pos: number[] = [], idx: number[] = [];
      pts.forEach((p, i) => {
        const nxt = pts[Math.min(i + 1, pts.length - 1)], prv = pts[Math.max(i - 1, 0)];
        const d = new THREE.Vector2(nxt.x - prv.x, nxt.y - prv.y).normalize();
        for (const sgn of [-1, 1]) {
          const x = p.x - d.y * width / 2 * sgn, y = p.y + d.x * width / 2 * sgn;
          pos.push(x, y, surf(x, y) + lift);
        }
        if (i) { const b = (i - 1) * 2; idx.push(b, b + 1, b + 2, b + 1, b + 3, b + 2); }
      });
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      return new THREE.Mesh(g, mat);
    };

    // Devi's saree: pallu draped from the right hip across the front and over the left shoulder,
    // gold border on both edges, gold band at the hem (blouse and skirt colours are set in setCharacter)
    const pallu = this.ethnic.saree.clone(); pallu.side = THREE.DoubleSide;
    const border = this.ethnic.gold.clone(); border.side = THREE.DoubleSide;
    const palluPath: [number, number][] = [[-0.33, -0.9], [-0.06, -0.52], [0.2, -0.17], [0.37, 0.07]];
    this.deviBody.add(ribbon(palluPath, 0.34, 0.022, surface(femaleR), border));
    this.deviBody.add(ribbon(palluPath, 0.28, 0.03, surface(femaleR), pallu));
    const hem = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.022, 8, 48), this.ethnic.gold);
    hem.rotation.x = Math.PI / 2;
    hem.scale.set(1, 0.55, 1);
    hem.position.y = -1.63;
    this.deviBody.add(hem);
    this.deviBody.visible = false;
    this.group.add(this.deviBody);

    // Dev's kurta: band collar, gold placket and buttons down the chest
    const band = new THREE.MeshStandardMaterial({ color: "#f1e4c4", roughness: 0.75, side: THREE.DoubleSide });
    const collarBand = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.15, 0.07, 24, 1, true), band);
    collarBand.position.y = 0.12;
    this.devParts.add(collarBand);
    this.devParts.add(ribbon([[0, 0.1], [0, -0.2], [0, -0.48]], 0.05, 0.006, surface(maleR), border));
    for (const y of [0.0, -0.14, -0.28, -0.42]) {
      const button = new THREE.Mesh(new THREE.SphereGeometry(0.017, 10, 8), this.ethnic.gold);
      button.scale.set(1, 1, 0.5);
      button.position.set(0, y, surface(maleR)(0, y) + 0.012);
      this.devParts.add(button);
    }
    this.devParts.visible = false;
    this.group.add(this.devParts);

    // head (pivot at neck top)
    this.head.position.set(0, 0.22, 0);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.29, 28, 20), this.mats.skin);
    skull.scale.set(0.92, 1.12, 0.98);
    skull.position.set(0, 0.36, 0);
    this.skull = skull;
    const hair = new THREE.Mesh(new THREE.SphereGeometry(0.305, 28, 20, 0, Math.PI * 2, 0, Math.PI * 0.42), this.mats.hair);
    hair.scale.set(0.93, 1.13, 1.0);
    hair.position.set(0, 0.37, -0.015);
    hair.rotation.x = -0.38;
    this.hairCap = hair;
    this.head.add(skull, hair);
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.032, 12, 10), this.mats.dark);
      eye.position.set(s * 0.105, 0.4, 0.265);
      this.eyes.push(eye);
      const white = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 10), new THREE.MeshStandardMaterial({ color: "#fffaf0" }));
      white.position.copy(eye.position); white.position.z -= 0.018;
      this.eyeWhites.push(white);
      const lid = new THREE.Mesh(new THREE.SphereGeometry(0.046, 12, 10), this.mats.skin);
      lid.position.copy(eye.position); lid.position.z += 0.008;
      lid.scale.set(1, 0.001, 0.5);
      this.lids.push(lid);
      this.head.add(white, lid);
      const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.016, 0.10, 4, 8), this.mats.hair);
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
    this.nose = nose;
    this.femaleNose = new THREE.Mesh(new THREE.SphereGeometry(0.03, 14, 10), this.mats.skin);
    this.femaleNose.scale.set(1.1, 0.9, 0.8);
    this.femaleNose.position.set(0, 0.315, 0.285);
    this.femaleNose.visible = false;
    this.head.add(this.femaleNose);
    this.mouth = new THREE.Mesh(new THREE.SphereGeometry(0.05, 14, 10), this.mats.mouth);
    this.mouth.scale.set(1.2, 0.35, 0.4);
    this.mouth.position.set(0, 0.2, 0.27);
    this.head.add(nose, this.mouth);
    // female look: long hair behind the head, side locks, eyelashes
    // long hair: full back section, side panels over the ears, and long strands falling in front onto the chest
    const back = new THREE.Mesh(new THREE.SphereGeometry(0.36, 28, 20), this.mats.hair);
    back.scale.set(1.0, 1.9, 0.45);
    back.position.set(0, -0.05, -0.3);
    this.femaleParts.add(back);
    // curly hair: a dense crown of small curls plus full locks that taper toward the ends
    const curlGeo = new THREE.SphereGeometry(1, 12, 9);
    let seed = 7;
    const rand = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
    const curl = (pos: THREE.Vector3, r: number) => {
      const c = new THREE.Mesh(curlGeo, this.mats.hair);
      const k = r * (0.8 + rand() * 0.4);
      c.scale.set(k, k, k * 0.9);
      c.position.copy(pos);
      this.anyaHair.add(c);
    };
    // crown: curls over the head surface; forehead clear, ears covered
    const FN = 260, fGolden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < FN; i++) {
      const y = 1 - (i / (FN - 1)) * 2, rad = Math.sqrt(1 - y * y), th = fGolden * i;
      const d = new THREE.Vector3(Math.cos(th) * rad, y, Math.sin(th) * rad);
      if (!(d.z > 0.25 ? d.y > 0.6 : d.z > -0.15 ? d.y > -0.15 : d.y > -0.7)) continue;
      curl(new THREE.Vector3(d.x * 0.31 * 0.97, 0.36 + d.y * 0.31 * 1.14, d.z * 0.31), 0.058);
    }
    // a lock = clusters of 3 curls along a path, shrinking toward the tip
    const lock = (pts: THREE.Vector3[], r0: number, r1: number) => {
      const total = pts.slice(1).reduce((n, p, i) => n + p.distanceTo(pts[i]), 0);
      const steps = Math.round(total / 0.055);
      const curve = new THREE.CatmullRomCurve3(pts);
      for (let i = 0; i <= steps; i++) {
        const t = i / steps, r = r0 + (r1 - r0) * t;
        for (let j = 0; j < 3; j++) {
          const ang = (j / 3) * Math.PI * 2 + i * 1.3;
          curl(curve.getPoint(t).add(new THREE.Vector3(Math.cos(ang) * r * 0.9, (rand() - 0.5) * 0.03, Math.sin(ang) * r * 0.6)), r);
        }
      }
    };
    for (const s of [-1, 1]) {
      // from beside the ear, over the shoulder, down the front of the chest (kept outside the shirt)
      lock([new THREE.Vector3(s * 0.3, 0.3, -0.02), new THREE.Vector3(s * 0.3, 0.0, 0.05),
        new THREE.Vector3(s * 0.31, -0.2, 0.36), new THREE.Vector3(s * 0.31, -0.5, 0.36), new THREE.Vector3(s * 0.31, -0.78, 0.32)], 0.07, 0.045);
      // back volume behind the shoulders
      lock([new THREE.Vector3(s * 0.18, 0.2, -0.3), new THREE.Vector3(s * 0.22, -0.2, -0.36), new THREE.Vector3(s * 0.24, -0.6, -0.36)], 0.09, 0.06);
      const cheek = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 10), this.blush);
      cheek.scale.set(1, 0.7, 0.25);
      cheek.position.set(s * 0.15, 0.27, 0.262);
      this.femaleParts.add(cheek);
    }
    this.femaleParts.visible = false;
    this.head.add(this.femaleParts);
    this.anyaHair.visible = false;
    this.head.add(this.anyaHair);

    // Devi: straight hair over the ears, bindi, gold jhumka earrings
    for (const s of [-1, 1]) {
      const from = new THREE.Vector3(s * 0.25, 0.5, -0.02), to = new THREE.Vector3(s * 0.29, -0.06, 0.0);
      const dir = to.clone().sub(from);
      const panel = new THREE.Mesh(new THREE.CapsuleGeometry(0.1, dir.length(), 10, 18), this.mats.hair);
      panel.position.copy(from).addScaledVector(dir, 0.5);
      panel.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
      panel.scale.set(1, 1, 0.75);
      const stud = new THREE.Mesh(new THREE.SphereGeometry(0.022, 12, 10), this.ethnic.gold);
      stud.position.set(s * 0.255, 0.21, 0.1);
      const bell = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.045, 14), this.ethnic.gold);
      bell.position.set(s * 0.255, 0.175, 0.1);
      this.deviParts.add(panel, stud, bell);
    }
    const bindi = new THREE.Mesh(new THREE.SphereGeometry(0.016, 12, 10), this.ethnic.bindi);
    bindi.scale.set(1, 1, 0.4);
    bindi.position.set(0, 0.465, 0.272);
    this.deviParts.add(bindi);
    this.deviParts.visible = false;
    this.head.add(this.deviParts);
    // male: short curls over the top, sides and back of the head; forehead and ears left clear
    const maleCurl = new THREE.SphereGeometry(1, 12, 9);
    const N = 220, golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2, rad = Math.sqrt(1 - y * y), th = golden * i;
      const d = new THREE.Vector3(Math.cos(th) * rad, y, Math.sin(th) * rad);
      const keep = d.z > 0.2 ? d.y > 0.6 : d.z > -0.2 ? d.y > 0.18 : d.y > -0.3;
      if (!keep) continue;
      const c = new THREE.Mesh(maleCurl, this.mats.hair);
      c.scale.setScalar(0.05 + ((i * 37) % 10) * 0.002);
      c.position.set(d.x * 0.3 * 0.94, 0.36 + d.y * 0.3 * 1.14, d.z * 0.3 * 1.0);
      this.maleParts.add(c);
    }
    this.head.add(this.maleParts);

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
      mcp.rotation.set(c * MCP, 0, 0); pip.rotation.set(c * PIP, 0, 0); dip.rotation.set(c * DIP, 0, 0);
      // fan: index (nearest the thumb) tilts toward the thumb side, pinky away
      h.fingerBase[i].rotation.z = -h.side * (1.5 - i) * st.spread * 0.2;
    }
    const tc = Math.min(1, Math.max(0, st.c[0]));
    const out = Math.min(1, Math.max(0, st.thumbOut));
    // abduction swings the thumb away from the palm; curl folds it across the palm
    h.thumbBase.rotation.z = -h.side * ((8 + 52 * out) * DEG * (1 - 0.7 * tc));
    h.thumbBase.rotation.y = h.side * (-0.5 * tc);
    h.thumbBase.rotation.x = tc * 0.55 + (1 - out) * 0.1;
    h.thumbJoints[0].rotation.set(tc * 0.5, 0, 0);
    h.thumbJoints[1].rotation.set(tc * 0.75, 0, 0);
    h.thumbJoints[2].rotation.set(tc * 0.6, 0, 0);
    if (st.fingers) {
      [...h.thumbJoints, ...h.fingers.flat()].forEach((joint, i) => joint.quaternion.fromArray(st.fingers![i]).normalize());
    }
  }

  /** Two-bone IK from shoulder to wrist; returns the elbow. Elbow is pushed down/out/back. */
  private solveArm(side: "R" | "L", wrist: THREE.Vector3) {
    const { a: S, b: pole, dir, q, up } = this.tmp;
    const sx = side === "R" ? -SHOULDER_X : SHOULDER_X;
    S.set(sx, this.shoulderRaise[side], 0);
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

  applyPose(p: AvatarPose) { this.applyJoints(p); }

  /** Resolved v1/v2 pose. Absent joints retain the original curl model. */
  applyJoints(p: AvatarPose) {
    const bounded = (v: number | undefined, lo: number, hi: number) => Math.max(lo, Math.min(hi, Number.isFinite(v) ? v! : 0));
    this.shoulderRaise = { R: bounded(p.torso?.shoulder_raise_right, 0, 0.3), L: bounded(p.torso?.shoulder_raise_left, 0, 0.3) };
    this.shoulders.forEach(sh => { sh.position.y = sh.position.x < 0 ? this.shoulderRaise.R : this.shoulderRaise.L; });
    this.group.rotation.set(bounded(p.torso?.lean_x, -30, 30) * DEG, 0, bounded(p.torso?.lean_z, -30, 30) * DEG);
    const face = resolvedFace(p);
    for (const side of ["R", "L"] as const) {
      const st = p[side];
      const w = this.solveArm(side, new THREE.Vector3(st.p[0], st.p[1], st.p[2]));
      const hand = this.hands[side];
      this.poseHand(hand, st);
      hand.root.position.copy(w); // wrist snaps to the reachable point
    }
    this.head.rotation.set(...p.head.map(v => bounded(v * EXPRESSION_STYLE.headGain, -90, 90) * DEG) as [number, number, number], "YXZ");
    // Smooth monotone display response; channel sign/range and authored timing stay intact.
    const response = (v: number | undefined) => Math.sin(bounded(v, 0, 1) * Math.PI / 2);
    this.brows.forEach((b, i) => {
      const down = response(i === 0 ? face.brow_down_right : face.brow_down_left);
      const up = response(face.brow_inner_up);
      b.position.y = 0.48 + EXPRESSION_STYLE.browRaise * up - EXPRESSION_STYLE.browLower * down;
      b.position.x = (i === 0 ? -1 : 1) * (0.105 - 0.014 * down);
      b.rotation.z = Math.PI / 2 + (i === 0 ? -1 : 1) * EXPRESSION_STYLE.browSlope * down;
    });
    const round = response(face.mouth_round);
    this.mouth.scale.set(1.2 + response(face.mouth_wide) * 1.2 - round * 0.55, 0.28 + 2.1 * response(face.mouth_open) + round * 0.85, 0.4 + round * 0.3);
    this.eyes.forEach((eye, i) => {
      eye.position.x = (i === 0 ? -1 : 1) * 0.105 + bounded(face.gaze_x, -1, 1) * 0.024;
      eye.position.y = 0.4 + bounded(face.gaze_y, -1, 1) * 0.020;
      // Cosmetic squint from existing gaze/brow channels; no new semantic channel.
      const tension = response(i === 0 ? face.brow_down_right : face.brow_down_left);
      const squint = Math.max(Math.abs(bounded(face.gaze_x, -1, 1)), Math.abs(bounded(face.gaze_y, -1, 1))) * EXPRESSION_STYLE.gazeSquint + tension * EXPRESSION_STYLE.browSquint;
      const closure = Math.max(squint, bounded(face.eye_blink, 0, 1));
      eye.scale.y = 1 - 0.98 * closure;
      this.lids[i].scale.y = Math.max(0.001, closure);
    });
  }

  /** World targets for the optional experimental glTF retargeter. */
  jointTargets() {
    this.group.updateMatrixWorld(true);
    return Object.fromEntries((["R", "L"] as const).map(side => {
      const shoulder = new THREE.Vector3(side === "R" ? -SHOULDER_X : SHOULDER_X, this.shoulderRaise[side], 0).applyMatrix4(this.group.matrixWorld);
      return [side, { shoulder, elbow: this.arms[side].elbow.getWorldPosition(new THREE.Vector3()), wrist: this.hands[side].root.getWorldPosition(new THREE.Vector3()), rotation: this.hands[side].root.getWorldQuaternion(new THREE.Quaternion()) }];
    })) as Record<"R" | "L", { shoulder: THREE.Vector3; elbow: THREE.Vector3; wrist: THREE.Vector3; rotation: THREE.Quaternion }>;
  }

  /** Idle motion layered on top of any pose (breathing). */
  idle(time: number) {
    const s = 1 + Math.sin(time * 1.6) * 0.008;
    this.torso.scale.set(this.torsoX * s, 1, 0.58 * s);
    this.femaleTorso.scale.set(s, 1, 0.55 * s);
    this.maleTorso.scale.set(s, 1, 0.55 * s);
  }

  setCharacter(kind: CharacterId) {
    if (kind === this.character) return;
    this.character = kind;
    const f = kind === "anya" || kind === "devi";
    const sleeve = kind === "dev" ? this.ethnic.kurta : kind === "devi" ? this.ethnic.blouse : this.mats.shirt;
    this.femaleParts.visible = f;
    this.anyaHair.visible = kind === "anya";
    this.deviParts.visible = kind === "devi";
    this.deviBody.visible = kind === "devi";
    this.devParts.visible = kind === "dev";
    this.femaleTorso.material = kind === "devi" ? this.ethnic.blouse : this.mats.shirt;
    this.femaleSkirt.material = kind === "devi" ? this.ethnic.saree : this.mats.shirt;
    this.maleTorso.material = kind === "dev" ? this.ethnic.kurta : this.mats.shirt;
    this.mats.mouth.color.set(f ? "#7a2f2f" : "#7a2a35");
    this.mouth.scale.set(f ? 0.95 : 1.2, f ? 0.3 : 0.35, 0.4);
    this.brows.forEach(b => b.scale.set(f ? 0.6 : 1, f ? 0.95 : 1, f ? 0.6 : 1));   // thinner brows
    this.skull.scale.set(f ? 0.95 : 0.92, f ? 1.06 : 1.12, 0.98);   // rounder face
    this.neck.scale.set(f ? 0.82 : 1, 1, f ? 0.82 : 1);
    this.maleTorso.visible = !f;
    this.maleParts.visible = kind === "arav";          // Dev keeps the neat smooth hair
    this.femaleTorso.visible = f;
    this.femaleSkirt.visible = f;
    this.femaleShirtParts.visible = kind === "anya";
    this.hairCap.scale.set(f ? 1.0 : 0.93, f ? 1.17 : 1.13, f ? 1.06 : 1.0);   // fuller crown, no fringe
    for (const a of Object.values(this.arms)) {                 // sleeves to the elbow in the outfit colour
      a.upper.material = sleeve;
      a.elbow.material = sleeve;
    }
    this.eyeWhites.forEach(w => { w.visible = !f; });             // small dot eyes
    this.eyes.forEach(e => e.scale.set(f ? 0.85 : 1, f ? 1.15 : 1, f ? 0.85 : 1));
    this.nose.visible = !f;
    this.femaleNose.visible = f;
  }

  setColors(c: RigColors) {
    this.mats.skin.color.set(c.skin); this.mats.shirt.color.set(c.shirt);
    this.mats.hair.color.set(c.hair); this.mats.accent.color.set(c.accent);
    (this.vneck?.material as THREE.MeshStandardMaterial | undefined)?.color.set(c.skin);
  }

  dispose() {
    this.group.traverse((o) => { const m = o as THREE.Mesh; m.geometry?.dispose?.(); });
    const materials = new Set<THREE.Material>();
    this.group.traverse(o => { const mat = (o as THREE.Mesh).material; if (mat) (Array.isArray(mat) ? mat : [mat]).forEach(m => materials.add(m)); });
    materials.forEach(m => m.dispose());
  }
}
