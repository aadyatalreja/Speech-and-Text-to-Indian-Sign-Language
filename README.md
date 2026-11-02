# SignAI — experimental English text/speech to sign playback

SignAI turns English text into a gloss representation and resolves it to signer
videos, avatar clips, or explicitly labeled spelling placeholders. **It is not
currently a validated English-to-ISL translator.**

The bundled repository contains demo assets; run `python backend/tools/repo_stats.py` for current counts.
Alphabet/digit availability and review counts are reported by `repo_stats.py`. Grammar examples contain
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

Use Python 3.12 and Node 22 (see `.nvmrc`); CI also tests Python 3.11. From the root,
create/activate a virtual environment and install:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
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
npm ci
npm run dev
```

Open http://localhost:5173; `/lab.html` previews clips, NMM overrides, and
transitions. Vite proxies API/WebSocket, sign assets, and generated videos.
Docker: after creating `.env`, run `docker compose up --build`. The backend image
includes FFmpeg and WordNet and runs as a non-root user. The frontend is a
multi-stage Node 22 build served by nginx at port 5173; nginx proxies API,
WebSocket, referenced sign assets, and generated exports. The backend is internal
to the Compose network. Only nginx publishes a host port. It overwrites forwarded
client-IP headers; the backend trusts that private network. Do not expose the
backend port or attach untrusted services to that network with this proxy setup.
For Vite hot reload use `docker compose -f docker-compose.yml -f dockercompose.dev.yml up --build`
(Docker Compose 2.24.4+ is required for the port override). Sign assets are mounted
from `./backend/data/signs` read-only; exports use the `generated-videos` named
volume. Keep the default container paths when using these mounts. Neither
rebuilds nor `docker compose down` remove exports; `down -v` does.
Authentication and public HTTPS hosting still need deployment configuration.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | `mock` or `api` |
| `LLM_API_KEY` | empty | Backend-only Anthropic key; not needed in mock mode |
| `LLM_MODEL` | `claude-sonnet-5-5` | Claude Messages API model ID |
| `LLM_MAX_TOKENS` | `2048` | Output budget for structured gloss JSON, 256–8192 |
| `LLM_TIMEOUT_SECONDS` | `20` | SDK timeout per attempt, 0.1–300 seconds; retries can extend total request time. |
| `LLM_MAX_RETRIES` | `2` | SDK retries with exponential backoff, 0–10. |
| `LLM_ORDERING` | `code` | English-order model output followed by code operators; `model` retains legacy unverified model ordering. |
| `LLM_CACHE_SIZE` | `256` | Maximum successful API responses cached per process; `0` disables and clears the cache. |
| `LLM_CACHE_TTL_SECONDS` | `300` | Response-cache TTL, 0.1–86400 seconds. |
| `ENABLE_SYNONYM_FALLBACK` | `false` | Optional WordNet synonym/one-hop hypernym approximation in the deterministic English path; meaning may drift. |
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
Only verified examples compatible with the repository vocabulary from
`examples.jsonl` enter the stable prompt. The per-request shortlist still limits
accepted model glosses. That file is intentionally empty until 20–50 genuine reviewed examples
are contributed. See [the grammar review process](docs/ISL_GRAMMAR_REVIEW.md).

NMM numeric values come only from configured YAML rules; model-supplied poses
and verification claims are discarded. Shipped question/negation marker
mappings are empty and disabled. English question/negation metadata does not
validate ISL NMM. Sentence rules span multiple tokens; gloss rules can override
specific channels. Unspecified clip channels remain intact.

## English gap diagnostics and model processing

These are **English processing and repository-coverage features, not ISL grammar**.
`demo_function_word_filter_2` adds common English conjunctions, prepositions and
determiners as an enabled, explicitly unverified demo filter. Repository matches
always win. Dropping conjunctions/prepositions can lose meaning; filtering is not
linguistic validation. All-filter input retains explicit FS tokens to keep the
existing nonempty response contract.

`gloss_detail` and sequence items add optional `fs_reason` and `lemma_tried`:

| Reason | Meaning |
| --- | --- |
| `oov` | Deterministic English lookup found no repository entry, including after lemmatization. |
| `name_heuristic` | An unmatched capitalized word was conservatively kept intact as a possible name. |
| `model_unknown` | An out-of-vocabulary model gloss was converted to FS by defensive validation. |
| `explicit` | A token was explicitly supplied with `FS:`; it is never resolved back to a sign. |

`lemma_tried` records the first changed WordNet lemma, or the lowercase word if
none changes; it is null when no lemma was attempted (including potential names
and explicit model FS tokens). For example, BOUGHT can remain FS with `buy` as
the attempted lemma because BUY is absent. This is a vocabulary gap, not a
lemmatizer failure. The frontend currently ignores these diagnostic fields.

When enabled, WordNet fallback tries synonyms and one-hop hypernyms already in
the repository after ordinary lookup and before spelling. It never creates a
sign, promotes review status, or runs on potential names/capitalized unknown
words. It performs no word-sense disambiguation. `synonym_from` and a visible
**meaning may drift; not ISL grammar** notice disclose substitutions. Healthy API
output remains subject to the strict allowed vocabulary; the lexical fallback
is used by the deterministic English path (including API-failure fallback).
Leave it disabled when measuring baseline vocabulary gaps.

```text
python backend/tools/coverage_report.py eval/domain_sentences.txt --json-output eval/reports/english_coverage.json --markdown-output eval/reports/english_coverage.md
```

The input has 60 plain English sentences, 12 each for campus, hospital, travel,
shopping and family. The report always uses the local deterministic path: no key,
network request or paid model call, even if `LLM_PROVIDER=api`. JSON and Markdown
include each sentence's gloss/FS count, overall FS rate and frequency-ranked OOV
words with attempted lemmas. FS rate is FS tokens divided by emitted gloss tokens
in successfully measured sentences, not an accuracy score. Names/explicit tokens
contribute to FS count but are excluded from the OOV ranking. Blank lines are
ignored; empty/unmeasurable input has a null rate. Measurement/input errors are
reported, and normal CLI exits are always 0: this is informational, not a gate.
CI appends the report to the `tests` job summary with synonyms disabled.

The backend now uses the pinned official [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python/tree/v0.75.0).
One `AsyncAnthropic` client is created at startup when API mode has a key, reused
for requests and closed at shutdown; standalone async callers initialize lazily
and should call `close_client()` when finished. The key remains backend-only.
SDK/transport error bodies and headers are never logged by application fallback
handling. Timeout, exhausted retries, refusals, truncated/malformed output or
missing tools retain `mock-fallback` and the existing availability notice.

The forced `emit_gloss` tool schema restricts each gloss to the allowed enum or
an explicit FS token pattern. `parse_llm_json` and `validate_vocabulary` remain
independent defensive layers. In `LLM_ORDERING=code`, the prompt requests English
word order plus sentence metadata; code applies the same deterministic English
filters/demo operators as the mock path, then the shared marker stage. Only rules
actually applied by code are reported. Model-provided rule-use/review claims are
discarded. `model` preserves legacy ordering and explicitly discloses all
possible draft influences plus the unreviewed model-ordering notice.

Stable instructions, configured rules and reviewed examples occupy a system
block with `cache_control`; per-request vocabulary follows it. DEBUG records only
`cache_read` and `cache_creation` token counts. Service-side prompt-cache savings
are not guaranteed: eligibility/prefix matching apply, and a changed tool-schema
vocabulary can invalidate the prefix. No paid cache-savings measurement was made.

A separate LRU/TTL response cache stores only successfully validated API results.
Its key includes whitespace-normalized text (case is preserved for names), a
vocabulary/repository hash, rule/example file mtimes, model and ordering, plus
prompt/config fingerprints. Edits invalidate cached responses; values are copied
between requests. The cache is process-local, retained in memory only, and cleared
at shutdown. It may hold user input/outputs for the configured TTL. Failed API
calls and deterministic fallbacks are not cached. Different workers have separate
clients/caches, and simultaneous identical misses may each make a request.

TODO (maintainer): check model access and real SDK/cache behaviour with an
authorized backend key before relying on live API operation. Tests use fake SDK
clients exclusively and do not establish model quality or cache savings. Licensed
assets, signer-authored examples and signer/linguist evaluation remain pending.

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
unit/build checks separately from an evaluation-readiness job that reports
exit 2 as informational in the job summary and succeeds without scores. All
other nonzero evaluator exits still fail that job. A passing software suite is not a
passing linguistic evaluation. No production model evaluation was performed.

## Verification

```text
cd backend
python -m pytest -q
```

```text
cd frontend
npm test
npx tsc --noEmit
npm run build
```

From the root: `python backend/tools/validate_signs.py`. Optional
`backend/requirements-video-test.txt` installs a local binary for synthetic
FFmpeg integration tests; production export still uses the configured binary.
Fixtures test mechanics only, with no invented signs represented as real ISL.
See [the task completion report](docs/IMPLEMENTATION_REPORT.md).

## Development commands and CI

Activate the virtual environment, install `backend/requirements-dev.txt`, and
run `npm ci` in `frontend`. Runtime-only installs use `backend/requirements.txt`;
pytest, coverage and Ruff are development dependencies. Optional ingestion and
synthetic-video test packages remain separate.

With GNU Make installed: `make test` runs both suites, TypeScript checking and
the production build; `make lint` runs Ruff lint/format checks; `make dev` starts
the Docker Vite override. On Windows without Make, run the commands in the
Verification section plus `python -m ruff check .` and
`python -m ruff format --check .` from the root.

The required software job remains exactly `tests` (Python 3.12, Node 22), with
pip/npm caches, metadata validation, Ruff, TypeScript and frontend tests/build.
It requires the Python 3.11/3.12 backend test matrix to succeed, including when
that matrix fails or is cancelled; coverage (excluding test files) appears in each matrix job summary.
The separate `docker-build` job builds both images and
waits for backend HTTP health. TODO (repository maintainer): confirm branch
protection requires the stable `tests` check after the first remote CI run.
No remote CI run or branch-protection change is implied by local verification.

## Backend limits and asset exposure

| Setting | Default | Meaning |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated HTTP(S) origins, without paths, credentials or wildcards. |
| `RATE_LIMIT_TRANSLATE_PER_MIN` | `30` | Per-IP token bucket shared by POST translation and WebSocket connections. |
| `RATE_LIMIT_VIDEO_PER_MIN` | `5` | Separate per-IP export token bucket. |
| `MAX_VIDEO_JOBS` | `2` | Maximum simultaneous export jobs per backend process. |
| `GENERATED_TTL_MINUTES` | `60` | Completed generated-file retention; cleanup on startup and every 10 minutes. |

All numeric limits must be positive integers. Compose passes these through `.env`.
Buckets start full and refill continuously; HTTP exhaustion returns 429 with
`Retry-After`. WebSocket exhaustion sends `{type: "error", error: ...}` and closes
with code 1008. Busy export workers return 429 and `Retry-After: 1`. Limits and
concurrency are process-local: multiple workers/replicas each have independent
state. Direct backend requests use the socket peer, ignoring forwarded headers
unless a trusted proxy is configured by the ASGI server.

Video sequences contain 1–50 tokens, each at most 64 characters, matching
`(?:FS:)?[A-Za-z0-9_'-]+`; invalid requests return 422 with the existing error shape.
Expiry removes old files directly inside the generated folder, never `.gitkeep`,
symlinks or active temporary directories. Download links may expire after cleanup.

`/signs` serves only repository-referenced video/avatar clips and non-rejected
alphabet clips; raw `signs.json`, `alphabet/manifest.json` and unreferenced files
return 404. `GET /api/alphabet` returns version/characters with only `source`,
`licence`, `signer`, `review_status`, `duration` and `clip`; rejected characters
are omitted. Reviewers, review history, import fields and evidence stay private, including
audit fields written into referenced clip JSON by offline review tooling.
Grammar/marker YAML and examples are parsed once per file mtime/size; edits reload
without restarting. Blocking sequence/timing work runs outside the event loop.

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

### Live previews and limits

Live translates typed text and speech interim text after a 600 ms debounce.
New text cancels the active preview; only an explicit translation or final speech
sentence is remembered in history. A rate limit pauses previews for Retry-After
and shows the resume time. Cancellation does not undo server work already started.
The complete sentence gloss is required before M4 applies ordering in code:
this is not token-level LLM streaming. Understanding is sent once that result
exists, then each sign is built in a worker and emitted for incremental playback.
Sign data and alphabet metadata reload on the next request when file mtime/size
changes; corrupt updates retain the last good snapshot and log an error.

For current sign and alphabet counts run `python backend/tools/repo_stats.py`.
See [local INCLUDE import instructions](docs/INCLUDE_IMPORT.md).

### Experimental avatar v2, Indian-language input and reports

V1 avatar clips and applyPose remain supported. Optional v2 finger joints,
face/gaze/eyelids, torso channels, conversion and SYNTHETIC lab previews are
explained in [AVATAR_V2.md](docs/AVATAR_V2.md). VITE_AVATAR_MODEL_URL optionally
loads your own supported glTF humanoid, with procedural fallback; no model is
bundled and you must hold its usage/distribution rights.

The language selector supports Hindi and Kannada for typing and browser speech.
Non-English input is machine-translated to English first in API mode; the editable
English intermediate and explicit unverified/failure notices are shown. Report
buttons submit opt-in wrong-sign reports for human prioritization; no review status
changes automatically. See [the review and privacy guide](docs/EVALUATION_AND_REVIEW.md).
