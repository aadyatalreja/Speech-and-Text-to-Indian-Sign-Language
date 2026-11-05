import { describe, expect, it, vi } from "vitest";
import * as THREE from "three";
import { compileClip, eulerYXZToQuat, restPose, sampleClip, slerp } from "./pose";
import { fingerspellClip, hasLetters, spellDuration } from "./alphabet";
import { DEMO_SIGNS } from "./demoSigns";
import { getClip, retimeForAvatar, willFingerspell, avatarLabel, prefetchClips, videoLabel } from "./library";
import type { SignClip } from "./types";

const item = (gloss: string, extra = {}) => ({ gloss, sign_id: null, available: true, duration: 1, pause_after: 0.2, asset_type: "demo", video_url: null, ...extra });

describe("pose maths", () => {
  it("euler YXZ matches three.js", () => {
    for (const e of [[0, 0, 0], [30, 45, 60], [-90, 20, 180], [10, -170, 5]] as const) {
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(e[0] * Math.PI / 180, e[1] * Math.PI / 180, e[2] * Math.PI / 180, "YXZ"));
      const m = eulerYXZToQuat([e[0], e[1], e[2]]);
      const dot = Math.abs(q.x * m[0] + q.y * m[1] + q.z * m[2] + q.w * m[3]);
      expect(dot).toBeGreaterThan(0.99999);
    }
  });
  it("slerp halfway between yaw 0 and 90 is yaw 45", () => {
    const mid = slerp(eulerYXZToQuat([0, 0, 0]), eulerYXZToQuat([0, 90, 0]), 0.5);
    const ref = eulerYXZToQuat([0, 45, 0]);
    for (let i = 0; i < 4; i++) expect(mid[i]).toBeCloseTo(ref[i], 6);
  });
});

describe("clips", () => {
  const clip: SignClip = { version: 1, id: "t", gloss: "T", kind: "demo", keys: [
    { t: 0, R: { p: [0, 0, 0], shape: "fist" } },
    { t: 1, R: { p: [1, 2, 3], shape: "open" } },
  ] };
  it("interpolates and holds channels", () => {
    const c = compileClip(clip);
    expect(sampleClip(c, 0).R.p).toEqual([0, 0, 0]);
    expect(sampleClip(c, 1).R.p).toEqual([1, 2, 3]);
    expect(sampleClip(c, 0.5).R.p[1]).toBeCloseTo(1, 5);
    expect(sampleClip(c, 0.5).R.c[1]).toBeCloseTo(0.5, 5);
    expect(sampleClip(c, 0.5).L.p).toEqual(restPose().L.p); // untouched hand stays at rest
  });
  it("null returns a hand to rest", () => {
    const c = compileClip({ ...clip, keys: [{ t: 0, R: { p: [0, 0, 0] } }, { t: 1, R: null }] });
    expect(sampleClip(c, 1).R.p).toEqual(restPose().R.p);
  });
  it("every demo clip compiles with in-range times", () => {
    for (const d of DEMO_SIGNS) {
      expect(d.keys.every((k) => k.t >= 0 && k.t <= 1)).toBe(true);
      expect(() => sampleClip(compileClip(d), 0.5)).not.toThrow();
    }
  });
});

describe("resolution order and fingerspelling", () => {
  it("keeps generated videos labeled until every repository item is verified", () => {
    expect(videoLabel([])).toContain("not verified ISL");
    expect(videoLabel([item("HELLO")])).toContain("not verified ISL");
    expect(videoLabel([item("HELLO", { review_status: "verified" })])).toContain("reviewed assets");
    expect(videoLabel([item("HELLO", { review_status: "verified" }), item("YOU", { review_status: "unverified" })])).toContain("not verified ISL");
  });
  it("labels imported dataset clips unverified unless repository review metadata verifies them", async () => {
    const source: SignClip = { version: 1, id: "import-fixture", gloss: "FIXTURE", kind: "dataset",
      review_status: "verified", keys: [{ t: 0, R: { p: [-0.3, 0, 0] }, L: { p: [0.3, 0, 0] } },
        { t: 1, R: { p: [-0.3, 0.2, 0] }, L: { p: [0.3, 0.2, 0] } }] };
    const mockFetch = vi.fn(async (url: RequestInfo | URL) => new Response(JSON.stringify(
      String(url).endsWith("/api/alphabet") ? { version: 1, characters: {} } : source), { status: 200 }));
    vi.stubGlobal("fetch", mockFetch);
    try {
      const draft = item("FIXTURE", { clip_url: "/signs/clips/import-fixture.json", review_status: "unverified" });
      await prefetchClips([draft]);
      const clip = getClip(draft);
      expect(avatarLabel(clip)).toContain("not verified ISL");
      expect(sampleClip(clip, 1).L.p).toEqual([0.3, 0.2, 0]);
      const reviewed = item("FIXTURE", { clip_url: "/signs/clips/reviewed-fixture.json", review_status: "verified" });
      await prefetchClips([reviewed]);
      expect(avatarLabel(getClip(reviewed))).toContain("reviewed dataset clip");
      expect(avatarLabel(getClip({ ...reviewed, review_status: "unverified" }))).toContain("not verified ISL");
    } finally { vi.unstubAllGlobals(); }
  });
  it("treats FS: as metadata, never as letters or a demo sign", () => {
    expect(spellDuration("FS:PRIYA")).toBe(spellDuration("PRIYA"));
    expect(getClip(item("FS:HELLO", { fs_reason: "explicit" })).clip.kind).toBe("fingerspell");
    expect(willFingerspell(item("FS:HELLO", { fs_reason: "explicit" }))).toBe(true);
    expect(avatarLabel(getClip(item("FS:PRIYA", { fs_reason: "explicit" })))).toContain("Chart-based avatar poses (unreviewed)");
  });
  it("animates digits without imported assets", () => {
    const clip = getClip(item("FS:1"));
    expect(clip.clip.gloss).toBe("FS:1");
    expect(hasLetters("FS:1")).toBe(true);
    expect(clip.clip.keys.some((k) => k.R != null)).toBe(true);
    expect(avatarLabel(clip)).toContain("Chart-based avatar poses (unreviewed)");
  });
  it("demo gloss uses the demo clip, unknown gloss is fingerspelled", () => {
    expect(getClip(item("HELLO")).clip.kind).toBe("demo");
    expect(getClip(item("COLLEGE")).clip.kind).toBe("fingerspell");
    expect(getClip(item("FS:WATER", { fs_reason: "oov" })).clip.kind).toBe("fingerspell");
    expect(willFingerspell(item("COLLEGE"))).toBe(true);
    expect(willFingerspell(item("HELLO"))).toBe(false);
  });
  it("an unfetched clip_url falls back instead of breaking", () => {
    expect(getClip(item("HELLO", { clip_url: "/signs/clips/none.json" })).clip.kind).toBe("demo");
  });
  it("spelling handles underscores, repeats and junk", () => {
    expect(hasLetters("123")).toBe(true);
    const c = fingerspellClip("HELLO_YOU");
    expect(c.keys.length).toBeGreaterThan(9);
    expect(c.keys.every((k) => k.t >= 0 && k.t <= 1)).toBe(true);
    expect(() => compileClip(fingerspellClip("???"))).not.toThrow();
  });
  it("retimes only fingerspelled items and keeps identity otherwise", () => {
    const demoOnly = [item("HELLO")];
    expect(retimeForAvatar(demoOnly)).toBe(demoOnly);
    const out = retimeForAvatar([item("FS:COLLEGE", { duration: 1.3, fs_reason: "explicit" })]);
    expect(out[0].duration).toBeCloseTo(spellDuration("COLLEGE"), 5);
    expect(out[0].duration).toBeGreaterThan(1.3);
  });
});

it("plays an inline iSign clip through the existing avatar compiler", () => {
  const inlineClip: SignClip = { version: 2, id: "fixture-1", gloss: "ISIGN_SEQUENCE", kind: "dataset",
    duration: 2, keys: [{ t: 0, R: { p: [-0.2, 0, 0.5] } }, { t: 1, R: { p: [-0.2, 0.2, 0.5] } }] };
  const result = item("ISIGN_SEQUENCE", { inline_clip: inlineClip });
  expect(sampleClip(getClip(result), 1).R.p).toEqual([-0.2, 0.2, 0.5]);
  expect(retimeForAvatar([result])[0].duration).toBe(2);
  expect(willFingerspell(result)).toBe(false);
});


it("points ME toward the body and YOU away from it", () => {
  const me = sampleClip(getClip(item("ME")), 1).R;
  const you = sampleClip(getClip(item("YOU")), 1).R;
  const pointingDirection = (hand: typeof me) =>
    new THREE.Vector3(0, 1, 0).applyQuaternion(new THREE.Quaternion(...hand.q));
  expect(pointingDirection(me).z).toBeLessThan(-0.8);
  expect(pointingDirection(you).z).toBeGreaterThan(0.8);
  expect(me.p[0] - you.p[0]).toBeGreaterThan(0.4);
});

it("turns ME upside down while keeping the same final pointing direction as I", () => {
  const i = sampleClip(getClip(item("I")), 1).R;
  const me = sampleClip(getClip(item("ME")), 1).R;
  const rotate = (axis: THREE.Vector3, hand: typeof me) =>
    axis.applyQuaternion(new THREE.Quaternion(...hand.q));
  expect(rotate(new THREE.Vector3(0, 1, 0), me).dot(rotate(new THREE.Vector3(0, 1, 0), i))).toBeCloseTo(1);
  expect(rotate(new THREE.Vector3(0, 0, 1), me).dot(rotate(new THREE.Vector3(0, 0, 1), i))).toBeCloseTo(-1);
});

it("keeps the hand-authored ME and YOU poses when dataset entries advertise clips", () => {
  for (const gloss of ["ME", "YOU"]) {
    const original = getClip(item(gloss));
    const imported = item(gloss, { asset_type: "dataset", clip_url: "/signs/clips/imported.json" });
    expect(getClip(imported)).toBe(original);
    expect(willFingerspell(imported)).toBe(false);
  }
});
