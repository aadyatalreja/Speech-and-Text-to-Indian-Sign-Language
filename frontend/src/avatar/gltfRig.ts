/** Experimental named-bone retargeting; no model is bundled or fetched by default. */
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { curlJoints, resolvedFace, FACE_KEYS } from "./pose";
import type { AvatarPose } from "./types";
import type { AvatarRig } from "./rig";

export function disposeModel(root: THREE.Object3D) {
  root.traverse(object => {
    const mesh = object as THREE.Mesh;
    mesh.geometry?.dispose();
    const materials = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
    materials.forEach(material => {
      for (const value of Object.values(material)) if (value instanceof THREE.Texture) value.dispose();
      material.dispose();
    });
  });
}

export class GltfAvatar {
  private bones = new Map<string, THREE.Bone>();
  private bind = new Map<THREE.Bone, THREE.Quaternion>();
  private axes = new Map<THREE.Bone, THREE.Vector3>();
  private handOffsets = new Map<THREE.Bone, THREE.Quaternion>();
  constructor(readonly group: THREE.Group) {
    group.traverse(object => {
      if ((object as THREE.Bone).isBone) {
        const bone = object as THREE.Bone;
        const name = bone.name.toLowerCase().replace(/^mixamorig[:_]?/, "").replace(/[^a-z0-9]/g, "");
        this.bones.set(name, bone); this.bind.set(bone, bone.quaternion.clone());
      }
    });
    for (const name of ["head", "spine", "leftarm", "leftforearm", "lefthand", "rightarm", "rightforearm", "righthand"]) this.bone(name);
    group.updateMatrixWorld(true);
    const left = this.bone("leftarm").getWorldPosition(new THREE.Vector3());
    const right = this.bone("rightarm").getWorldPosition(new THREE.Vector3());
    const width = left.distanceTo(right);
    if (!Number.isFinite(width) || width < 1e-6) throw new Error("Invalid humanoid shoulders");
    group.scale.multiplyScalar(1 / width);
    group.position.multiplyScalar(1 / width).sub(left.add(right).multiplyScalar(0.5 / width));
    group.updateMatrixWorld(true);
    for (const side of ["left", "right"]) {
      const upper = this.bone(side + "arm"), fore = this.bone(side + "forearm"), hand = this.bone(side + "hand");
      this.axes.set(upper, fore.position.clone().normalize().applyQuaternion(this.bind.get(upper)!));
      this.axes.set(fore, hand.position.clone().normalize().applyQuaternion(this.bind.get(fore)!));
      // Recover a neutral palm frame from the supplied finger bases if available.
      const index = this.bones.get(side + "handindex1"), pinky = this.bones.get(side + "handpinky1");
      let neutral = new THREE.Quaternion();
      if (index && pinky) {
        const wrist = hand.getWorldPosition(new THREE.Vector3());
        const a = index.getWorldPosition(new THREE.Vector3()).sub(wrist), b = pinky.getWorldPosition(new THREE.Vector3()).sub(wrist);
        const y = a.clone().add(b).normalize();
        const z = (side === "right" ? a.clone().cross(b) : b.clone().cross(a)).normalize();
        const x = y.clone().cross(z).normalize(); z.crossVectors(x, y).normalize();
        neutral.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
      }
      this.handOffsets.set(hand, neutral.invert().multiply(hand.getWorldQuaternion(new THREE.Quaternion())));
    }
  }
  private bone(name: string): THREE.Bone {
    const aliases: Record<string, string> = { leftarm: "leftupperarm", rightarm: "rightupperarm", leftforearm: "leftlowerarm", rightforearm: "rightlowerarm" };
    const bone = this.bones.get(name) ?? this.bones.get(aliases[name]);
    if (!bone) throw new Error(`Unsupported humanoid bone: ${name}`);
    return bone;
  }
  private aim(bone: THREE.Bone, from: THREE.Vector3, to: THREE.Vector3) {
    const parent = bone.parent!.getWorldQuaternion(new THREE.Quaternion()).invert();
    const direction = to.clone().sub(from).normalize().applyQuaternion(parent);
    bone.quaternion.setFromUnitVectors(this.axes.get(bone)!, direction).multiply(this.bind.get(bone)!);
    bone.updateWorldMatrix(false, true);
  }
  apply(pose: AvatarPose, procedural: AvatarRig) {
    const targets = procedural.jointTargets();
    const spine = this.bone("spine"), head = this.bone("head");
    spine.quaternion.copy(this.bind.get(spine)!).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler((pose.torso?.lean_x ?? 0) * Math.PI/180, 0, (pose.torso?.lean_z ?? 0) * Math.PI/180)));
    head.quaternion.copy(this.bind.get(head)!).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...pose.head.map(v => v * Math.PI/180) as [number,number,number], "YXZ")));
    this.group.updateMatrixWorld(true);
    for (const [side, label] of [["R", "right"], ["L", "left"]] as const) {
      const target = targets[side];
      const upper = this.bone(label + "arm");
      upper.position.copy(upper.parent!.worldToLocal(target.shoulder.clone()));
      this.group.updateMatrixWorld(true);
      this.aim(upper, target.shoulder, target.elbow);
      this.aim(this.bone(label + "forearm"), target.elbow, target.wrist);
      const hand = this.bone(label + "hand");
      hand.quaternion.copy(hand.parent!.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(target.rotation).multiply(this.handOffsets.get(hand)!));
      const joints = pose[side].fingers ?? curlJoints(pose[side].c);
      ["thumb", "index", "middle", "ring", "pinky"].forEach((finger, f) => {
        for (let j = 0; j < 3; j++) {
          const bone = this.bones.get(`${label}hand${finger}${j + 1}`);
          if (bone) bone.quaternion.copy(this.bind.get(bone)!).multiply(new THREE.Quaternion().fromArray(joints[f * 3 + j]));
        }
      });
    }
    const face = resolvedFace(pose);
    this.group.traverse(object => {
      const mesh = object as THREE.Mesh;
      if (!mesh.morphTargetDictionary || !mesh.morphTargetInfluences) return;
      for (const [name, index] of Object.entries(mesh.morphTargetDictionary)) {
        if (FACE_KEYS.includes(name as keyof typeof face)) mesh.morphTargetInfluences[index] = face[name as keyof typeof face] ?? 0;
      }
    });
  }
  dispose() { disposeModel(this.group); }
}

export async function loadGltfAvatar(url: string): Promise<GltfAvatar> {
  const gltf = await new GLTFLoader().loadAsync(url);
  try { return new GltfAvatar(gltf.scene); }
  catch (error) { disposeModel(gltf.scene); throw error; }
}
