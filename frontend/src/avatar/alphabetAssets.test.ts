import { describe, expect, it, vi } from "vitest";
import { AlphabetAssets, validateCharacterClip, type CharacterAsset } from "./alphabetAssets";
import { buildSpelling, spellingLabel } from "./alphabet";
import { compileClip, sampleClip } from "./pose";
import type { SignClip } from "./types";

// Synthetic software fixtures; these are not real ISL letters or digits.
const fixture = (symbol: string): SignClip => ({ version: 1, id: `fixture:${symbol}`, gloss: symbol, kind: "dataset", keys: [
  { t: 0, R: { p: [-0.3, 0, 0] }, L: { p: [0.3, 0.2, 0] } },
  { t: 1, R: { p: [-0.3, 0.1, 0] }, L: { p: [0.3, 0.4, 0] } },
] });
const asset = (symbol: string, review_status: CharacterAsset["review_status"] = "verified"): CharacterAsset => ({
  clip: fixture(symbol), duration: 1.2, source: "synthetic software fixture", licence: "test only", signer: "synthetic", review_status,
});
const entry = (symbol: string, extra = {}) => ({ clip: `${symbol}.json`, source: "synthetic software fixture",
  licence: "test only", signer: "synthetic", review_status: "verified", duration: 1.2, notes: "test only", ...extra });
const fetcher = (characters: Record<string, unknown>, failures: string[] = []) => vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input);
  if (failures.includes(url)) return new Response("missing", { status: 404 });
  return new Response(JSON.stringify(url.endsWith("manifest.json") ? { version: 1, characters } : fixture(url.split("/").pop()!.replace(".json", ""))), { status: 200 });
});

describe("character clip loading", () => {
  it("loads licensed/provenanced clips once and notifies timing subscribers", async () => {
    const store = new AlphabetAssets(), fetch = fetcher({ A: entry("A"), "1": entry("1") });
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);
    await Promise.all([store.load(fetch), store.load(fetch)]);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(store.characters.get("A")!.clip.keys[0].L!.p).toEqual([0.3, 0.2, 0]);
    expect(store.characters.has("1")).toBe(true);
    expect(listener).toHaveBeenCalledOnce();
    expect(store.getRevision()).toBe(1);
    unsubscribe();
  });
  it("falls back per character for missing files, metadata, or unsafe paths", async () => {
    const store = new AlphabetAssets();
    const fetch = fetcher({ A: entry("A"), B: entry("B", { licence: null }),
      C: entry("C", { clip: "../C.json" }), D: entry("D") }, ["/signs/alphabet/D.json"]);
    await store.load(fetch);
    expect([...store.characters.keys()]).toEqual(["A"]);
    expect(fetch.mock.calls.some(([url]) => String(url).includes(".."))).toBe(false);
  });
  it("keeps a failed manifest playable using existing placeholders", async () => {
    const store = new AlphabetAssets();
    await store.load(fetcher({}, ["/signs/alphabet/manifest.json"]));
    expect(store.characters.size).toBe(0);
    expect(spellingLabel(buildSpelling("ABC", store.characters))).toContain("not the ISL alphabet");
  });
  it("rejects a corrupt handshape instead of inventing a replacement", () => {
    const clip = fixture("A");
    clip.keys[0].R!.shape = "invented_shape";
    expect(() => validateCharacterClip(clip, "A")).toThrow();
    expect(() => validateCharacterClip(fixture("B"), "A")).toThrow();
  });
});

describe("spelled word composition", () => {
  it("uses real-clip fixtures for both hands and keeps provenance", () => {
    const available = new Map([["A", asset("A")], ["1", asset("1")]]);
    const result = buildSpelling("FS:A1", available);
    const pose = sampleClip(compileClip(result), 0);
    expect(pose.R.p).toEqual([-0.3, 0, 0]);
    expect(pose.L.p).toEqual([0.3, 0.2, 0]);
    expect(result.spelling!.assets.map((a) => a.character)).toEqual(["A", "1"]);
    expect(result.spelling!.duration).toBeCloseTo(2.82);
    expect(spellingLabel(result)).toContain("Reviewed alphabet clips");
    expect(available.get("A")!.clip.keys[0].t).toBe(0);
  });
  it("falls back only for missing letters and keeps the not-ISL label", () => {
    const result = buildSpelling("FS:AB", new Map([["A", asset("A")]]));
    expect(result.spelling!.missing).toEqual(["B"]);
    expect(result.spelling!.assets.map((a) => a.character)).toEqual(["A"]);
    expect(spellingLabel(result)).toContain("not the ISL alphabet");
    expect(spellingLabel(result)).toContain("B");
  });
  it("never labels unreviewed supplied clips as verified", () => {
    const result = buildSpelling("A", new Map([["A", asset("A", "in_review")]]));
    expect(result.spelling!.unverified).toEqual(["A"]);
    expect(spellingLabel(result)).toContain("not verified ISL");
  });
  it("preserves missing digits and unsupported characters as text-only entries", () => {
    const result = buildSpelling("FS:001?", new Map());
    expect(result.spelling!.textOnly).toEqual(["0", "1", "?"]);
    expect(result.keys.every((key) => key.R === null && key.L === null)).toBe(true);
    expect(spellingLabel(buildSpelling("FS:123", new Map()))).toContain("Digits shown as text only");
  });
  it("keeps repeated letters distinct and resets an omitted hand for the next character", () => {
    const oneHand = asset("B");
    oneHand.clip.keys.forEach((key) => { delete key.L; });
    const result = buildSpelling("AAB", new Map([["A", asset("A")], ["B", oneHand]]));
    expect(result.keys.some((key) => key.t > 0 && key.R === null && key.L === null)).toBe(true);
    const last = sampleClip(compileClip(result), 1);
    expect(last.L.p).not.toEqual([0.3, 0.4, 0]);
    expect(result.keys.every((key) => key.t >= 0 && key.t <= 1)).toBe(true);
  });
  it("refreshes cached playback and timing after assets arrive", async () => {
    vi.resetModules();
    const { alphabetAssets } = await import("./alphabetAssets");
    const { getClip, retimeForAvatar, avatarLabel } = await import("./library");
    const item = { gloss: "FS:A", sign_id: null, available: false, duration: 0.6, pause_after: 0,
      asset_type: "none", video_url: null };
    const before = getClip(item);
    await alphabetAssets.load(fetcher({ A: entry("A") }));
    const after = getClip(item);
    expect(after).not.toBe(before);
    expect(avatarLabel(after)).toContain("Reviewed alphabet clips");
    expect(retimeForAvatar([item])[0].duration).toBeCloseTo(1.5);
  });
});
