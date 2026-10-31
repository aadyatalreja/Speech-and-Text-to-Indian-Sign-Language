import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { SignItem } from "../types/translation";
import { getClip } from "./library";
import { PoseFollower, restPose, sampleClip, compileClip, transitionPose, type CompiledClip } from "./pose";
import type { AvatarPose } from "./types";
import { mergeNmm } from "./nmm";
import { AvatarRig, type RigColors } from "./rig";

interface Props {
  /** sign being performed, or null for idle */
  item: SignItem | null;
  /** 0..1 progress through this item (including its trailing pause) */
  progress: number;
  playing: boolean;
  /** perform this clip instead of resolving one from the item (used by the clip lab) */
  override?: CompiledClip | null;
  previousOverride?: CompiledClip | null;
  /** reports the clip currently on stage so the UI can label it honestly */
  onClip?: (c: CompiledClip | null) => void;
  /** reports WebGL failure so the caller can fall back to the text stage */
  onUnsupported?: () => void;
}

const cssRgb = (name: string, fallback: string) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v ? `rgb(${v.split(/\s+/).join(",")})` : fallback;
};
const colors = (): RigColors => ({ skin: "#e3b393", shirt: cssRgb("--accent", "#c2410c"), hair: "#2b2220", accent: cssRgb("--accent3", "#d97706") });

export default function AvatarCanvas({ item, progress, playing, override, previousOverride, onClip, onUnsupported }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const live = useRef({ item, progress, playing, override, previousOverride });
  live.current = { item, progress, playing, override, previousOverride };
  const cb = useRef({ onClip, onUnsupported });
  cb.current = { onClip, onUnsupported };

  useEffect(() => {
    const el = host.current;
    if (!el) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      cb.current.onUnsupported?.();
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    el.appendChild(renderer.domElement);
    Object.assign(renderer.domElement.style, { width: "100%", height: "100%", display: "block" });

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, 16 / 9, 0.1, 50);
    camera.position.set(0, -0.25, 5.0);
    camera.lookAt(0, -0.25, 0);
    scene.add(new THREE.HemisphereLight("#ffffff", "#8a8179", 1.35));
    const key = new THREE.DirectionalLight("#ffffff", 1.9);
    key.position.set(2.5, 3, 5);
    const rim = new THREE.DirectionalLight("#ffd9b8", 0.7);
    rim.position.set(-3, 1.5, -2);
    scene.add(key, rim);

    const rig = new AvatarRig(colors());
    scene.add(rig.group);

    const resize = () => {
      const w = el.clientWidth || 1, h = el.clientHeight || 1;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      // keep the whole upper body in frame for narrow containers
      camera.position.z = 5.0 * Math.max(1, (16 / 9) / camera.aspect) ** 0.9;
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    // re-colour when the light/dark theme toggles
    const mo = new MutationObserver(() => rig.setColors(colors()));
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    const follower = new PoseFollower();
    let last = performance.now(), raf = 0, lastClip: CompiledClip | null | undefined;
    const idle = restPose();
    let markedSource: CompiledClip | null = null, markedItem: SignItem | null = null, markedClip: CompiledClip | null = null;
    let previousEnd: AvatarPose | null = null, sequenceKey = "", lastProgress = 0;

    const frame = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      const { item: it, progress: pr, override: ov, previousOverride: previous } = live.current;
      let target = idle;
      let clip: CompiledClip | null = null;
      if (it) {
        clip = ov ?? getClip(it);
        const key = `${it.sequence_index ?? it.gloss}:${clip.clip.id}`;
        if (key !== sequenceKey || (ov && lastProgress > 0.9 && pr < 0.1)) {
          previousEnd = markedClip ? sampleClip(markedClip, 1) : null;
          sequenceKey = key;
        }
        lastProgress = pr;
        if (clip !== markedSource || it !== markedItem) {
          markedSource = clip; markedItem = it;
          const merged = mergeNmm(clip.clip, it.nmm);
          markedClip = merged === clip.clip ? clip : compileClip(merged);
        }
        const sign = it.duration / Math.max(0.001, it.duration + it.pause_after);
        target = transitionPose(previous ? sampleClip(previous, 1) : previousEnd, markedClip ?? clip,
          Math.min(1, pr / sign), it.transition_duration ?? 0.18, it.duration);
      } else {
        previousEnd = null; sequenceKey = ""; lastProgress = 0;
        markedSource = null; markedItem = null; markedClip = null;
      }
      if (clip !== lastClip) { lastClip = clip; cb.current.onClip?.(clip); }
      rig.applyPose(follower.follow(target, dt, it ? 18 : 9));
      rig.idle(now / 1000);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      mo.disconnect();
      rig.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div ref={host} className="absolute inset-0" aria-hidden />;
}
