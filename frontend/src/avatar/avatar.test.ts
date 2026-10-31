import { describe, expect, it, vi } from "vitest";
import * as THREE from "three";
import { compileClip, eulerYXZToQuat, restPose, sampleClip, slerp } from "./pose";
import { fingerspellClip, hasLetters, spellDuration, spellableLetters } from "./alphabet";
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
      String(url).endsWith("manifest.json") ? { version: 1, characters: {} } : source), { status: 200 }));
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
    expect(spellableLetters("FS:PRIYA")).toEqual(spellableLetters("PRIYA"));
    expect(spellDuration("FS:PRIYA")).toBe(spellDuration("PRIYA"));
    expect(getClip(item("FS:HELLO")).clip.kind).toBe("fingerspell");
    expect(willFingerspell(item("FS:HELLO"))).toBe(true);
    expect(avatarLabel(getClip(item("FS:PRIYA")))).toContain("not the ISL alphabet");
  });
  it("keeps missing digits as text without fabricating handshapes", () => {
    const clip = getClip(item("FS:1"));
    expect(clip.clip.gloss).toBe("FS:1");
    expect(hasLetters("FS:1")).toBe(false);
    expect(clip.clip.keys.every((k) => k.R === null)).toBe(true);
    expect(avatarLabel(clip)).toContain("Digits shown as text only");
  });
  it("demo gloss uses the demo clip, unknown gloss is spelled", () => {
    expect(getClip(item("HELLO")).clip.kind).toBe("demo");
    expect(getClip(item("COLLEGE")).clip.kind).toBe("fingerspell");
    expect(willFingerspell(item("COLLEGE"))).toBe(true);
    expect(willFingerspell(item("HELLO"))).toBe(false);
  });
  it("an unfetched clip_url falls back instead of breaking", () => {
    expect(getClip(item("HELLO", { clip_url: "/signs/clips/none.json" })).clip.kind).toBe("demo");
  });
  it("spelling handles underscores, repeats and junk", () => {
    expect(hasLetters("123")).toBe(false);
    const c = fingerspellClip("HELLO_YOU");
    expect(c.keys.length).toBeGreaterThan(9);
    expect(c.keys.every((k) => k.t >= 0 && k.t <= 1)).toBe(true);
    expect(() => compileClip(fingerspellClip("???"))).not.toThrow();
  });
  it("retimes only fingerspelled items and keeps identity otherwise", () => {
    const demoOnly = [item("HELLO")];
    expect(retimeForAvatar(demoOnly)).toBe(demoOnly);
    const out = retimeForAvatar([item("COLLEGE", { duration: 1.3 })]);
    expect(out[0].duration).toBeCloseTo(spellDuration("COLLEGE"), 5);
    expect(out[0].duration).toBeGreaterThan(1.3);
  });
});
