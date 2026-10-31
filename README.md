# SignAI — experimental English text/speech to sign playback

SignAI turns English text into a gloss representation and resolves it to signer
videos, avatar clips, or explicitly labeled spelling placeholders. **It is not
currently a validated English-to-ISL translator.**

The bundled repository contains **40 demo entries and no real sign recordings**.
All 36 alphabet/digit records are missing/unverified. Grammar examples contain
no reviewed translations, and the evaluation set contains only placeholders.
Real assets, licence/access decisions, and Deaf ISL signer/linguist review remain
human dependencies. Software tests do not establish linguistic correctness.

## Architecture and preserved interfaces

```text
English text / browser speech transcription
  → LLM or English normalization + editable demo grammar
  → structured gloss + sentence metadata + configured NMM
  → SignRepository → SignSequenceService / SignGenerator
  → signer video or SignClip v1 → AvatarRig.applyPose
```

Backend: FastAPI, Pydantic, NLTK WordNet, optional Anthropic Messages API, FFmpeg.
Frontend: React/Vite/TypeScript, Tailwind, Three.js. `SignRepository`,
`SignGenerator`, `AvatarRig.applyPose`, and SignClip v1 remain extension seams.
New clip metadata/duration fields are additive; legacy repository entries load.

## Local setup

Python 3.11+ and Node 22 are suitable for the provided workflow. From the root,
create/activate a virtual environment and install:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.venv\Scripts\python.exe -m nltk.downloader -d .venv/nltk_data wordnet
```

Use the equivalent environment Python path on macOS/Linux. WordNet is downloaded
once at setup, never silently during translation. Missing corpus data produces
an actionable setup error. If `.env` does not exist, copy `.env.example` to it.
Shell environment values take precedence over `.env`.

```text
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --port 8000
```

In another terminal:

```text
cd frontend
npm install
npm run dev
```

Open http://localhost:5173; `/lab.html` previews clips, NMM overrides, and
transitions. Vite proxies API/WebSocket, sign assets, and generated videos.
Docker: after creating `.env`, run `docker compose up --build`. The backend image
includes FFmpeg and WordNet. Production hosting/authentication are not provided
by this local demo configuration.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | `mock` or `api` |
| `LLM_API_KEY` | empty | Backend-only Anthropic key; not needed in mock mode |
| `LLM_MODEL` | `claude-sonnet-5-5` | Claude Messages API model ID |
| `LLM_MAX_TOKENS` | `2048` | Output budget for structured gloss JSON, 256–8192 |
| `TARGET_SIGN_LANGUAGE` | `ISL` | Target label; not a correctness guarantee |
| `INTER_SIGN_PAUSE` | `0.2` seconds | Sequence pause and export hold |
| `AVATAR_TRANSITION_SECONDS` | `0.18` | Pose blend, capped at half a sign |
| `DEMO_SIGN_DURATION` | `1.2` seconds | Explicit estimate when no asset duration exists |
| `FFMPEG_BINARY` | `ffmpeg` | Executable name/path for export |
| `FFPROBE_BINARY` | `ffprobe` | Executable name/path for video duration measurement |
| `SIGN_DATA_PATH` | `backend/data/signs` | Sign repository/asset directory |
| `GENERATED_VIDEO_PATH` | `backend/generated` | Generated export directory |
| `NLTK_DATA` | NLTK search defaults | Optional corpus directory |

Path overrides are relative to the backend process working directory unless
absolute. Use container paths in Docker. Numeric settings and model ID syntax
are validated. The model default was checked against
[Anthropic's official model overview](https://platform.claude.com/docs/en/models/overview)
on 2026-10-31; this does not establish account availability. An optional
read-only authenticated check is available:

```text
python backend/tools/check_model.py
```

No model request is made by that command without a key. API failures retain the
`mock-fallback` engine and a user-facing notice; no paid API call was required
for the software tests. Valid older Claude IDs can still be supplied via env.

## API compatibility

- `GET /api/health` returns the service status.
- `POST /api/translate` accepts `{text, source_language, target_sign_language}`.
  It retains flat `gloss`, `intent`, `entities`, `sequence`, `unknown_signs`,
  `confidence`, `engine`, `notice`; adds `gloss_detail`, `sentence`, and per-rule
  `grammar_rules`. Tokens contain `gloss`, `fs`, numeric `nmm`, review provenance,
  and optional symbolic referents. Sequence items include timing provenance,
  clip/video durations, transition duration, and asset review metadata.
- `WS /api/translate/stream` sends `understanding`, indexed `sign` items, then
  `done` (or `error`), with the same linguistic/review metadata.
- `POST /api/generate-video` accepts `{sequence: [gloss, ...]}` and returns
  `{video_url, missing_glosses, notice}`. Missing clips are skipped explicitly;
  no available video or an unavailable FFmpeg produces 422.

`FS:<WORD>` means character spelling. `unknown_signs` lists the unprefixed
unknown words. Repository availability is not equivalent to verified ISL.
The default confidence values are demo heuristics, not calibrated ISL accuracy.

## English lookup, vocabulary, and grammar

Lookup tries original gloss/aliases before WordNet inflections, preserving signs
such as PLEASE before function-word filtering. Common contractions are expanded;
numbers use whole-number entries or digits, preserving repetitions and zeros.
Unknown words and potential names use explicit FS tokens. Name detection is a
capitalization heuristic; ambiguous names can still match common words.

API prompts contain allowed repository glosses, or a deterministic keyword/
lemma/alias shortlist plus core function signs above 300 entries. Model aliases
are canonicalized only to allowed glosses; other tokens become FS, and malformed
output falls back. This constrains vocabulary, not semantic or ISL correctness.

Grammar operations and legacy demo phrases live in `data/grammar/isl_rules.yaml`
under the backend. Applied draft rules retain an **Unverified grammar** notice.
Only verified, vocabulary-compatible examples from `examples.jsonl` enter the
prompt. That file is intentionally empty until 20–50 genuine reviewed examples
are contributed. See [the grammar review process](docs/ISL_GRAMMAR_REVIEW.md).

NMM numeric values come only from configured YAML rules; model-supplied poses
and verification claims are discarded. Shipped question/negation marker
mappings are empty and disabled. English question/negation metadata does not
validate ISL NMM. Sentence rules span multiple tokens; gloss rules can override
specific channels. Unspecified clip channels remain intact.

## Sign metadata and licensed ingestion

Sign records retain `id`, `gloss`, `asset_type` (`demo`, `dataset`, `video`),
`video`, `clip`, and `keypoints`. Added optional fields include `aliases`, `lemma`,
`category`, `source`, `licence`, `signer`, `review_status`, `notes`, durations,
technical QA, import hashes, and review history. Old records default unverified.
Non-demo assets require provenance and referenced files must exist.

```text
python backend/tools/bulk_import.py manifest.csv --permissions permissions.json --intended-use "your reviewed use" --copy-video
python backend/tools/validate_signs.py
```

Imports are resumable/idempotent, preserve verified entries unless explicitly
forced, record QA, and always register new material as unverified. QA never
replaces signer review. Optional MediaPipe/OpenCV dependencies are separate.
See [ingestion](docs/INGESTION.md), [dataset licences/access](docs/LICENSES.md),
and [alphabet registration](backend/data/signs/alphabet/README.md).

## Playback and timing

Complete video sequences default to **Real signer videos**; partial sequences
default to Avatar. Explicit partial-video mode shows missing items as text cards.
Media completion drives video chaining; pause/resume/restart/speed are shared.
Combined export is an explicit action, normalizes size/fps/codec, and reports
omissions. See [video playback details](docs/VIDEO_PLAYBACK.md).

Timing uses local clip `duration`, measured FFprobe video duration, or recorded
asset metadata where available. `timing_source` discloses clip/video timing or
spelling/demo estimates. Only spelling uses the length formula; known demo
motions use the fixed configured estimate. The frontend updates to loaded clip/
character durations. Avatar transitions blend the previous pose into the next
clip rather than snapping to rest; these are engine interpolation, not reviewed
ISL coarticulation. The lab can scrub a previous/next demo pair. See
[timing and transition details](docs/TIMING.md).

Alphabet playback preserves both hands of supplied clips and their provenance.
Missing letters use the existing ASL-style approximations, explicitly **not the
ISL alphabet**. Missing digits/unsupported characters remain text-only. Only
entirely reviewed character assets drop that placeholder warning; assembled
word transitions are still not signer-certified.

## Evaluation and review

[Evaluation and local review](docs/EVALUATION_AND_REVIEW.md) describes JSON
review exports and the apply command. Reviews record a reviewer, comments,
evidence, and asset hashes; stale exports are refused. No public write endpoint
or automatic signer sign-off is provided.

```text
python eval/run_eval.py
```

**Current expected result: exit 2, NO_VERIFIED_ROWS, no scores.** Placeholder rows
must be replaced by signer-reviewed content before reporting metrics. CI runs
unit/build checks separately from an evaluation-readiness job that deliberately
fails while this prerequisite is unmet. A passing software suite is not a
passing linguistic evaluation. No production model evaluation was performed.

## Verification

```text
cd backend
python -m pytest -q
```

```text
cd frontend
npm test
npm run build
```

From the root: `python backend/tools/validate_signs.py`. Optional
`backend/requirements-video-test.txt` installs a local binary for synthetic
FFmpeg integration tests; production export still uses the configured binary.
Fixtures test mechanics only, with no invented signs represented as real ISL.
See [the task completion report](docs/IMPLEMENTATION_REPORT.md).

## Honest limitations

This system cannot currently express validated ISL classifiers, role shift,
agreement, discourse-dependent signing-space reference, or full non-manual
morphology. Symbolic pronoun labels do not create spatial indexing motion.
Topic/plural/tense analysis is incomplete; editable operators do not themselves
supply linguistic rules. Monocular pose conversion has noisy depth/orientation,
occlusion, and limited facial information. Static NMM channels and interpolated
transitions do not establish native signing. Regional/dialect variation and
comprehension require Deaf signer evaluation with licensed recordings.

Speech input is browser Web Speech transcription into editable English text.
Browser support varies; microphone access requires localhost/HTTPS. Some
browsers use an online speech service, so offline/private recognition is not
guaranteed. No multilingual translation or recognition accuracy is claimed.
