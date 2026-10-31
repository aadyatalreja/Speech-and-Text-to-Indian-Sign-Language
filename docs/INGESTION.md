# Bulk sign ingestion

`backend/tools/bulk_import.py` converts local, rights-reviewed isolated-sign
videos through MediaPipe Holistic and the existing converter. No dataset is
downloaded and all imported assets remain **unverified** pending signer review.

## Setup and command

Actual video extraction uses a separate Python 3.11 environment with:

```text
python -m pip install -r backend/requirements.txt -r backend/requirements-ingest.txt
```

The optional pins provide the legacy Holistic API; incompatible versions report
an error. The normal backend and CI fixture path need neither MediaPipe nor
OpenCV. No real-data extraction quality is claimed from fixture tests.

Copy `backend/tools/import_manifest.example.csv`. Required headers:

```text
gloss,aliases,category,video_path,source,licence,signer
```

Aliases can be pipe-separated or a quoted JSON list. Input paths are relative
to the CSV or absolute local paths. Glosses use uppercase letters/digits and
underscores. One row per gloss is supported; variants need reviewer-chosen IDs.
An optional `landmarks_path` column bypasses extraction using converter-format
Holistic JSON. `video_path` can then be empty unless copying videos; its header
remains required. If both are supplied, ensure they describe the same recording.

Read [LICENSES.md](LICENSES.md) and populate the permissions template with actual
source-specific review evidence. The default template authorizes nothing.

```text
python backend/tools/bulk_import.py path/to/manifest.csv --permissions path/to/permissions.json --intended-use "your reviewed intended use" --copy-video
```

Default output is `backend/data/signs`. Options include `--output <folder>`,
`--max-keys 24` (at least 2), `--qa-threshold 0.75`, and `--swap-hands`.
`--force` explicitly replaces a verified entry and resets it to unverified;
permissions are still required. Without it, verified rows are reported protected.

The command logs row results and prints a JSON summary; failures exit nonzero.
Each source must match an approval record's licence/intended use, processing and
redistribution permissions, reviewer, and evidence. This attestation cannot
automatically establish legal permission. It covers derived clips/landmarks as
well as video because the app serves them to browsers.

## Outputs and resume

Successful imports register `clip`, `keypoints`, optional `video`, provenance,
`review_status: unverified`, `qa`, `duration`, `needs_manual_review`, and hashes.
Clips themselves also carry provenance/review metadata and remain SignClip v1.
Files are written under `clips/`, `landmarks/`, and optionally `video/`, using
gloss/fingerprint filenames; the registry is atomically replaced per row.

Fingerprints include input hashes, row data, permissions, settings, and tool code.
Unchanged rows with intact outputs are skipped; changed rows update without
duplicating entries. Extraction is cached before conversion so interrupted rows
can reuse it. Successful rows survive later failures. Rerun after fixing failed
rows; missing/modified outputs are rebuilt. Old unreferenced files can remain
after updates or interruptions; this tool does not delete previous assets.

A per-folder OS lock prevents concurrent importers and releases on process exit.
External registry edits during a row are detected before commit. Avoid editing
the registry while importing. Restart the backend after importing because its
repository is cached; reload the browser too.

## QA and review

QA stores left/right/both-hand detection fractions, pose fraction, wrist jitter
(mean second difference in shoulder-width units per frame squared), frame/key
counts, converted duration, and a score. The heuristic-v1 score is:

```text
0.6 * both_hands + 0.2 * pose + 0.2 * max(0, 1 - jitter / 0.15)
```

Scores below the threshold set `needs_manual_review`. This is **not ISL
validation**: legitimate one-handed signs can score poorly, smooth incorrect
poses can score well, and jitter depends on motion/frame rate. All clips still
require Deaf signer review even when their technical manual-review flag is false.
Monocular depth, occlusion, facial detail, transitions, role shift, and spatial
reference remain limitations.

Run `python backend/tools/validate_signs.py`. Preview a generated clip by pasting
its JSON into `/lab.html`. Playback preserves both hands and uses repository
review metadata for the label; embedded clip claims cannot override an
unverified entry. Rights review and signer review are separate processes.

Tests cover five synthetic landmark/video-stub rows, optional extraction with
stub modules, QA, partial failures, fingerprints, missing outputs, force
protection, rights checks, and playback labels. A manual five-video run using
real licensed recordings and the pinned optional extractor remains pending;
no such recordings or dataset access agreements were supplied.
