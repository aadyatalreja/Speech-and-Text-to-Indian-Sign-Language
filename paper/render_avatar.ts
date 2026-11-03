/** CPU SVG projection of the actual procedural rig/clip pipeline, not generated art.
 * SVGRenderer differs from WebGL shading; geometry/pose and camera are shared.
 * Still frames cannot validate temporal signing or comprehension.
 */
import * as THREE from "three";
import { SVGRenderer } from "three/examples/jsm/renderers/SVGRenderer.js";
import { AvatarRig } from "../frontend/src/avatar/rig";
import { compileClip, sampleClip } from "../frontend/src/avatar/pose";
import { mergeNmm } from "../frontend/src/avatar/nmm";
import { getClip } from "../frontend/src/avatar/library";
import type { SignItem } from "../frontend/src/types/translation";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../.."); // bundled in paper/.cache
const escape = (s: unknown) => String(s).replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
// Minimal SVG DOM adapter: rendering math is Three's standard SVGRenderer.
class SvgNode {
  children: SvgNode[] = []; attributes: Record<string, string> = {}; style: Record<string, string> = {};
  constructor(public tag: string) {}
  get childNodes() { return this.children; }
  setAttribute(k: string, v: unknown) { this.attributes[k] = String(v); }
  appendChild(n: SvgNode) { this.children.push(n); return n; }
  removeChild(n: SvgNode) { this.children.splice(this.children.indexOf(n), 1); }
  get outerHTML(): string { return `<${this.tag} ${Object.entries(this.attributes).map(([k, v]) => `${k}="${escape(v)}"`).join(" ")}>${this.children.map(n => n.outerHTML).join("")}</${this.tag}>`; }
}
(globalThis as any).document = { createElementNS: (_namespace: string, tag: string) => new SvgNode(tag) };

function frame(item: SignItem, tau: number, withNmm: boolean, closeup = false): string {
  let source = getClip(item).clip;
  if (item.clip_url) {
    const base = resolve(root, "backend/data/signs");
    const local = resolve(base, decodeURIComponent(item.clip_url.replace(/^\/signs\//, "")));
    if (!local.startsWith(base + sep)) throw new Error("Clip path escapes sign repository");
    source = JSON.parse(readFileSync(local, "utf8"));
  }
  const compiled = compileClip(withNmm ? mergeNmm(source, item.nmm, item.nmm_rules) : source);
  const pose = sampleClip(compiled, tau);
  // The 'without' condition removes all nonmanual channels, including clip-authored ones.
  if (!withNmm) { pose.head = [0, 0, 0]; pose.brow = 0; pose.mouth = 0; pose.face = {}; }
  const rig = new AvatarRig({ skin: "#e3b393", shirt: "#25647a", hair: "#2b2220", accent: "#b06524" });
  rig.applyJoints(pose); // No random idle; deterministic pose sampling.
  const scene = new THREE.Scene(); scene.background = new THREE.Color("#f7fafc"); scene.add(rig.group);
  scene.add(new THREE.AmbientLight("#ffffff", 1.1));
  const light = new THREE.DirectionalLight("#ffffff", 1.5); light.position.set(2.5, 3, 5); scene.add(light);
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 50);
  camera.position.set(0, closeup ? 0.58 : -0.25, closeup ? 1.6 : 5.0);
  camera.lookAt(0, closeup ? 0.58 : -0.25, 0);
  const renderer = new SVGRenderer(); renderer.setSize(240, 240); renderer.setPrecision(2);
  renderer.render(scene, camera);
  const rendered = (renderer.domElement as unknown as SvgNode).outerHTML;
  rig.dispose();
  return rendered;
}

function strip(items: SignItem[], withNmm: boolean, closeup = false) {
  const frames = items.flatMap(item => (closeup ? [0.5] : [0.25, 0.75]).map(t => ({ item, t })));
  const cols = Math.min(4, frames.length || 1), rows = Math.ceil(frames.length / cols);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${cols * 260}" height="${rows * 280 + 35}" viewBox="0 0 ${cols * 260} ${rows * 280 + 35}"><rect width="100%" height="100%" fill="white"/>${frames.map(({ item, t }, i) => `<g transform="translate(${i % cols * 260 + 10},${Math.floor(i / cols) * 280 + 25})"><text font-size="12" font-family="sans-serif">${escape(item.gloss)} · t=${t} · ${withNmm ? "DEMO NMM" : "NMM OFF"}</text>${frame(item, t, withNmm, closeup).replace("<svg ", '<svg x="0" y="15" overflow="hidden" ')}</g>`).join("")}<text x="10" y="${rows * 280 + 20}" font-family="sans-serif" font-size="12">Actual engine geometry; demo assets/expressions are NOT verified ISL. Still frames do not measure comprehension.</text></svg>`;
}

const args = process.argv.slice(2);
const packetIndex = args.indexOf("--packet");
if (packetIndex >= 0) {
  const directory = resolve(args[packetIndex + 1]);
  const manifest = JSON.parse(readFileSync(resolve(directory, "manifest.json"), "utf8"));
  mkdirSync(resolve(directory, "frames"), { recursive: true });
  for (const item of manifest.items) writeFileSync(resolve(directory, item.frame_strip), strip(item.stimulus.translation.sequence, true));
} else {
  const input = resolve(args[args.indexOf("--input") + 1]);
  const output = resolve(args[args.indexOf("--output") + 1]);
  const response = JSON.parse(readFileSync(input, "utf8"));
  const item = response.sequence.find((i: SignItem) => i.nmm_rules?.length) ?? response.sequence[0];
  // One sentence, same sign/pose/time, differing only by the NMM intervention.
  const left = frame(item, 0.5, false, true).replace("<svg ", '<svg x="50" y="70" overflow="hidden" ');
  const right = frame(item, 0.5, true, true).replace("<svg ", '<svg x="390" y="70" overflow="hidden" ');
  writeFileSync(output, `<svg xmlns="http://www.w3.org/2000/svg" width="680" height="390" viewBox="0 0 680 390"><rect width="100%" height="100%" fill="white"/><text x="15" y="22" font-family="sans-serif" font-size="15">${escape(response.original_text)} — ${escape(item.gloss)}, same midpoint pose</text><text x="100" y="55" font-family="sans-serif" font-size="14">NMM channels OFF</text><text x="440" y="55" font-family="sans-serif" font-size="14">DEMO NMM channels ON</text>${left}${right}<text x="15" y="340" font-family="sans-serif" font-size="12">Actual procedural rig; head crop; no idle motion. Rendering comparison only.</text><text x="15" y="360" font-family="sans-serif" font-size="12">Demo expressions are NOT verified ISL grammar, timing or comprehension.</text></svg>`);
}
