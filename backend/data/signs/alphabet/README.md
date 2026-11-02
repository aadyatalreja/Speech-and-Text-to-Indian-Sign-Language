# Alphabet and digit assets

No real alphabet or digit clips are supplied. Every A–Z / 0–9 entry in
`manifest.json` is explicitly missing and unverified. Do not construct ISL
handshapes from memory or relabel the bundled placeholder alphabet as ISL.

To register a character after obtaining a licensed recording/reference:

1. Confirm that the licence permits the intended use and redistribution; retain
   source/permission evidence. Record the source, exact licence, and signer.
2. Convert the recording's landmarks using `backend/tools/mediapipe_to_clip.py`.
   Store the resulting SignClip v1 JSON here (for example `clips/A.json`), with
   `kind: dataset` and `gloss` matching the single uppercase character/digit.
   Preserve both hands. The upcoming Task 7 ingestion workflow is separate.
3. Update that manifest entry's `clip` (relative to this folder), `source`,
   `licence`, `signer`, `duration` (seconds, positive and at most 30), and `notes`.
   Keep `review_status: unverified` until a Deaf ISL signer reviews it. Use
   `in_review` during review and `verified` only after documented sign-off.
4. Run `python backend/tools/validate_signs.py`. It also validates this manifest
   and its referenced clips. File/metadata validity does not certify ISL or
   licence permissions. No file may be referenced outside this folder.
5. Reload the browser to fetch updated assets. `/lab.html?spell=A1` previews
   character playback. The loader fetches the manifest once per page session and
   caches valid clips; errors keep the labeled fallback until reload.

The frontend uses supplied character clips, retaining their right/left hand
channels, and preserves per-character provenance on assembled playback. Missing
letters use the existing placeholder; missing digits/unsupported symbols have no
invented poses and remain text-only. Any missing letter keeps the “not the ISL
alphabet” label; unreviewed supplied clips remain “not verified ISL.” Only a word
whose character assets are all verified receives the reviewed-character label.
Gaps/repeat separation are engine-generated; asset review does not certify the
full word or transitions as native signing. No claim of correct ISL is made by
the synthetic software fixtures in tests.
