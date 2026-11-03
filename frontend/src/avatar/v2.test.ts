import { describe, expect, it, vi } from "vitest";
import { adaptClip, compileClip, curlJoints, eulerYXZToQuat, PoseFollower, restPose, sampleClip, transitionPose } from "./pose";
import { AvatarRig } from "./rig";
import { validateCharacterClip } from "./alphabetAssets";
import { buildSpelling } from "./alphabet";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { GltfAvatar, loadGltfAvatar } from "./gltfRig";
import { mergeNmm, parseNmm } from "./nmm";
import type { FingerJoints, SignClipV1, SignClipV2 } from "./types";
import * as THREE from "three";
const joints = (angle: number) => Array.from({ length: 15 }, () => eulerYXZToQuat([angle, 0, 0])) as FingerJoints;
const v1: SignClipV1 = { version: 1, id: "v1", gloss: "SYNTHETIC", kind: "demo", keys: [{ t: 0, R: { p: [-0.3,0,0.4], shape: "fist" }, mouth: 0.4, brow: -0.2 }, { t: 1, R: { p: [-0.2,0,0.4] } }] };
const v2: SignClipV2 = { version: 2, id: "v2", gloss: "SYNTHETIC", kind: "demo", keys: [
  { t: 0, R: { p: [-0.3,0,0.4], fingers: joints(0), wrist: [0,0,0,1] }, face: { mouth_round: 0, eye_blink: 0, gaze_x: -1 }, torso: { lean_x: -10, shoulder_raise_left: 0 } },
  { t: 1, R: { fingers: joints(90), wrist: eulerYXZToQuat([0,90,0]) }, face: { mouth_round: 1, eye_blink: 1, gaze_x: 1 }, torso: { lean_x: 10, shoulder_raise_left: 0.2 } },
] };
describe("experimental v2 additive pose pipeline", () => {
  it("adapts v1 without changing defaults or mutating keys", () => {
    const saved = JSON.stringify(v1), adapted = adaptClip(v1);
    expect(adapted.version).toBe(2);
    expect(JSON.stringify(v1)).toBe(saved);
    expect(sampleClip(compileClip(v1), 1).R.c).toEqual([0.1,0,0,0,0]);
    expect(sampleClip(compileClip(v1), 0.5)).toEqual(sampleClip(compileClip(adapted), 0.5));
    expect(sampleClip(compileClip(v1), 0).face?.mouth_open).toBe(0.4);
  });
  it("slerps fifteen local joints and wrists, lerps sparse scalar channels", () => {
    const pose = sampleClip(compileClip(v2), 0.5);
    expect(pose.R.fingers).toHaveLength(15);
    pose.R.fingers!.forEach(q => q.forEach((value,i) => expect(value).toBeCloseTo(eulerYXZToQuat([45,0,0])[i])));
    expect(pose.R.q[1]).toBeCloseTo(eulerYXZToQuat([0,45,0])[1]);
    expect(pose.R.p).toEqual([-0.3,0,0.4]);
    expect(pose.face?.mouth_round).toBe(0.5);
    expect(pose.face?.eye_blink).toBe(0.5);
    expect(pose.face?.gaze_x).toBe(0);
    expect(pose.torso?.lean_x).toBe(0);
    expect(pose.torso?.shoulder_raise_left).toBe(0.1);
    expect(pose.L.p).toEqual(restPose().L.p);
  });
  it("blends v1/v2 in both directions and follows all channels", () => {
    const old = sampleClip(compileClip(v1), 1);
    const clip = compileClip(v2);
    expect(transitionPose(old, clip, 0, 0.2, 1)).toBe(old);
    const blend = transitionPose(old, clip, 0.1, 0.2, 1);
    expect(blend.R.fingers).toHaveLength(15);
    expect(blend.face!.gaze_x).toBeLessThan(0);
    const follower = new PoseFollower(); follower.snap(old);
    expect(follower.follow(sampleClip(clip, 1), 0.05).face!.mouth_round).toBeGreaterThan(0);
    const back = transitionPose(sampleClip(clip,1), compileClip(v1), 0.1,0.2,1);
    expect(back.R.fingers).toHaveLength(15);
    expect(back.torso!.shoulder_raise_left).toBeGreaterThan(0);
  });
  it("rejects invalid channels and joint arrays", () => {
    for (const face of [{ gaze_x: 2 }, { mouth_open: -1 }, { eye_blink: NaN }]) expect(() => compileClip({ ...v2, keys: [{t:0, face}] })).toThrow();
    expect(() => compileClip({ ...v2, keys: [{t:0, R:{ fingers: [] as unknown as FingerJoints }}] })).toThrow();
  });
  it("applies joints, resets to curl fallback and keeps applyPose delegating", () => {
    const rig = new AvatarRig({ skin:"#fff", shirt:"#888", hair:"#333", accent:"#ff0" });
    const detailed = sampleClip(compileClip(v2),1);
    rig.applyJoints(detailed);
    const internals = rig as unknown as { hands: {R: {fingers: THREE.Group[][]}}; mouth: THREE.Mesh; eyes: THREE.Mesh[]; lids: THREE.Mesh[] };
    expect(internals.hands.R.fingers[0][0].quaternion.x).toBeCloseTo(Math.SQRT1_2);
    expect(internals.lids[0].scale.y).toBe(1);
    rig.applyPose(sampleClip(compileClip(v1),1));
    expect(internals.hands.R.fingers[0][0].quaternion.x).toBe(0);
    expect(internals.lids[0].scale.y).toBeGreaterThan(0.001); // Brow-driven cosmetic squint.
    expect(curlJoints([0,0,0,0,0])).toHaveLength(15);
    rig.dispose();
  });
  it("merges bounded new NMM without inventing ISL rules", () => {
    const nmm = parseNmm({ gaze:[-1,1], mouth_shape:{round:0.8, wide:0.2} });
    const pose = sampleClip(compileClip(mergeNmm(v1,nmm)),0.5);
    expect(pose.face?.gaze_x).toBe(-1);
    expect(pose.face?.mouth_round).toBe(0.8);
    expect(() => parseNmm({gaze:[0,2]})).toThrow();
    expect(() => parseNmm({mouth_shape:{wide:2}})).toThrow();
    expect(() => new GltfAvatar(new THREE.Group())).toThrow("Unsupported humanoid");
  });
});

it("renders legible raised/furrowed brows, head angles, mouth shapes and gaze without changing input poses", () => {
  const rig = new AvatarRig({ skin: "#fff", shirt: "#888", hair: "#333", accent: "#ff0" });
  const geometry = rig as unknown as { brows: THREE.Mesh[]; mouth: THREE.Mesh; head: THREE.Group; lids: THREE.Mesh[]; eyes: THREE.Mesh[] };
  const raised = { ...restPose(), brow: 0.5, head: [5, 12, 3] as [number, number, number] };
  const saved = JSON.stringify(raised);
  rig.applyPose(raised);
  expect(geometry.brows[0].position.y - 0.48).toBeGreaterThan(0.05);
  expect(geometry.head.rotation.y).toBeCloseTo(14.4 * Math.PI / 180);
  rig.applyPose({ ...restPose(), brow: -0.5, face: { mouth_open: 0.5, mouth_wide: 0.5, gaze_x: 1 } });
  expect(geometry.brows[0].position.y).toBeLessThan(0.44);
  expect(Math.PI / 2 - geometry.brows[0].rotation.z).toBeGreaterThan(0.3); // Inner ends lower for furrow.
  expect(geometry.mouth.scale.y).toBeGreaterThan(1.5);
  const wide = geometry.mouth.scale.x;
  expect(geometry.lids[0].scale.y).toBeGreaterThan(0.2);
  rig.applyPose({ ...restPose(), face: { mouth_round: 1 } });
  expect(geometry.mouth.scale.x).toBeLessThan(wide);
  expect(geometry.mouth.scale.y).toBeGreaterThan(1);
  expect(JSON.stringify(raised)).toBe(saved);
  rig.dispose();
});

it("legacy NMM overrides explicit v2 face channels", () => {
  const clip: SignClipV2 = { ...v2, keys: [{t:0, face:{mouth_open:0.8,brow_inner_up:0.8}}] };
  const pose = sampleClip(compileClip(mergeNmm(clip,{mouth:0.2,brow:-0.4})),0);
  expect(pose.face?.mouth_open).toBe(0.2);
  expect(pose.face?.brow_inner_up).toBe(0);
  expect(pose.face?.brow_down_left).toBe(0.4);
});
it("loads a synthetic named-bone humanoid and exposes loading/validation failures for fallback", async () => {
  const group = new THREE.Group();
  const bone = (name: string, parent: THREE.Object3D, p: [number,number,number]) => { const b = new THREE.Bone(); b.name=name; b.position.set(...p); parent.add(b); return b; };
  const spine = bone("Spine",group,[0,0,0]);
  bone("Head",spine,[0,0.5,0]);
  for (const [side,x] of [["Right",-0.5],["Left",0.5]] as const) {
    const arm = bone(`mixamorig:${side}Arm`,spine,[x,0,0]);
    const fore = bone(`mixamorig:${side}ForeArm`,arm,[x,0,0]);
    const hand = bone(`mixamorig:${side}Hand`,fore,[x,0,0]);
    ["Thumb","Index","Middle","Ring","Pinky"].forEach((finger,i) => {
      let parent = hand;
      for(let j=1;j<=3;j++) parent=bone(`mixamorig:${side}Hand${finger}${j}`,parent,[j===1?(2-i)*0.025:0,0.1,0]);
    });
  }
  const loader = vi.spyOn(GLTFLoader.prototype,"loadAsync");
  loader.mockResolvedValue({scene:group} as Awaited<ReturnType<GLTFLoader["loadAsync"]>>);
  const model = await loadGltfAvatar("synthetic-test-only.glb");
  const rig = new AvatarRig({skin:"#fff",shirt:"#888",hair:"#333",accent:"#ff0"});
  const pose=sampleClip(compileClip(v2),0.5); rig.applyPose(pose);
  expect(() => model.apply(pose,rig)).not.toThrow();
  expect(group.scale.x).toBeCloseTo(1);
  loader.mockRejectedValue(new Error("synthetic network failure"));
  await expect(loadGltfAvatar("missing.glb")).rejects.toThrow("synthetic network failure");
  loader.mockResolvedValue({scene:new THREE.Group()} as Awaited<ReturnType<GLTFLoader["loadAsync"]>>);
  await expect(loadGltfAvatar("unsupported.glb")).rejects.toThrow("Unsupported humanoid");
  loader.mockRestore(); rig.dispose(); model.dispose();
});

it("keeps v2 channels in supplied character clips and resets them before v1 characters", () => {
  const first: SignClipV2 = { ...v2, gloss:"A",kind:"dataset",keys:[{t:0,R:{fingers:joints(30)},face:{eye_blink:1}}] };
  validateCharacterClip(first,"A");
  const meta = {duration:1,source:"SYNTHETIC",licence:"test only",signer:"none",review_status:"unverified" as const};
  const spelling=buildSpelling("AB",new Map([["A",{...meta,clip:first}],["B",{...meta,clip:{...v1,gloss:"B",kind:"dataset" as const}}]]));
  expect(spelling.version).toBe(2);
  const compiled=compileClip(spelling);
  expect(sampleClip(compiled,0).R.fingers).toHaveLength(15);
  expect(sampleClip(compiled,1).face?.eye_blink).toBe(0);
});
