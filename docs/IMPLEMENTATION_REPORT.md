# Implementation report

Checked locally on 2026-10-31. Tasks 1–11 have their software implementation in place. Human-authored linguistic content and licensed recordings remain pending where described below; this is an experimental system, not validated ISL translation.

## Task inventory

Paths below are relative to the project root. This is an implementation inventory, not a Git diff: this supplied folder has no `.git` directory, so per-task commits could not be created.

| Task | Implementation and principal files | Verification |
| --- | --- | --- |
| 1. Metadata/repository | `backend/models/sign.py`, `backend/services/sign_repository.py`, `backend/data/signs/signs.json`, `backend/tools/validate_signs.py`: optional provenance, aliases, lemmas, categories and review metadata; normalized lookup and validation. | `test_sign_repository.py`, `test_validate_signs.py`; existing registry loads and validates. |
| 2. English coverage | `backend/services/english_service.py`, `gloss_service.py`, requirements: WordNet lemmatization, repository lookup before stop-word removal, contractions, numbers and explicit `FS:` fallback. WordNet was chosen for its small dependency/model footprint. | `test_english_service.py`, `test_translation.py`: inflections, polite vocabulary, proper names and digits. |
| 3. Constrained vocabulary | `backend/services/vocabulary_service.py`, `llm_service.py`: allowed vocabulary, deterministic shortlist for large registries, alias resolution and output postvalidation. | `test_vocabulary.py`, `test_translation.py`: invented output becomes explicit fingerspelling. No live paid model call was made. |
| 4. Structured gloss/NMM | Backend models, `marker_service.py`, `llm_service.py`, translation API; `frontend/src/avatar/nmm.ts`, avatar canvas and lab: structured gloss and sentence intent, backward-compatible flat response, configured marker propagation. | `test_markers.py`, API/translation tests, `nmm.test.ts`; question/negation demo rules are enabled, unverified and require signer review. Engine interpolation is not reviewed ISL coarticulation. |
| 5. Grammar/review process | `backend/services/grammar_service.py`, `backend/data/grammar/isl_rules.yaml`, `examples.jsonl`, `docs/ISL_GRAMMAR_REVIEW.md`: editable operators, provenance/notices and verified-only prompt examples. | `test_grammar.py`, marker/translation tests. No fabricated 20–50 examples were supplied; the examples file awaits signer review. |
| 6. Alphabet/digits | `backend/models/alphabet.py`, `backend/data/signs/alphabet/`, `frontend/src/avatar/alphabetAssets.ts`, `alphabet.ts`, `library.ts`: asset-driven letter/digit composition and honest missing-asset fallback. | `test_alphabet.py`, `alphabetAssets.test.ts`; alphabet availability is reported by `python backend/tools/repo_stats.py`. |
| 7. Ingestion/QA | `backend/tools/bulk_import.py`, manifest/permission templates, converter adapter, `backend/requirements-ingest.txt`, `docs/INGESTION.md`, `LICENSES.md`: resumable import, QA, provenance, locking and verified-entry protection. | `test_bulk_import.py`, `test_mediapipe_to_clip.py`, fixture landmark tests. A real licensed five-video MediaPipe run remains pending supplied recordings/permission. |
| 8. Video playback/export | `frontend/src/services/videoPlayback.ts`, player/UI integration, `backend/services/video_service.py`, video API, `docs/VIDEO_PLAYBACK.md`: media-ended chaining, mode selection, mixed availability notices and normalized FFmpeg export. | `videoPlayback.test.ts`, `test_video_service.py`, API tests, real FFmpeg synthetic-color integration and browser smoke checks. Synthetic clips are not sign recordings. |
| 9. Timing/transitions | `backend/services/timing_service.py`, `sequence_service.py`, sign models/config; `frontend/src/services/timelinePlayback.ts`, `hooks/useSignPlayer.ts`, avatar pose/canvas/library, App and lab; `docs/TIMING.md`: actual asset durations, configurable gaps, elapsed-time playback and previous-end-pose blending. | `test_timing.py`, `timelinePlayback.test.ts`, `transitions.test.ts`; lab visually checked at start/midpoint of a transition between demo clips. Linguistic motion quality still needs signers. |
| 10. Evaluation/review | `eval/run_eval.py`, `isl_testset.jsonl`, `backend/tools/review_assets.py`, review metadata/filtering across loaders, `.github/workflows/checks.yml`, `docs/EVALUATION_AND_REVIEW.md`: verified-only metrics and offline export/apply decisions with evidence, audit history, stale-state checks and rejection handling. | `test_evaluation.py`, `test_review_assets.py`. Placeholder-only evaluator exits 2 without scores. CI workflow is authored but has not run remotely. |
| 11. Configuration/docs | `backend/config.py`, `backend/tools/check_model.py`, requirements, `.env.example`, `docker-compose.yml`, `README.md`, UI wording/title: environment validation, documented defaults, optional authenticated model lookup and honest limitations. | `test_config.py`, mocked model lookup tests, production build. No real API key/model-access check was performed. |

The compatibility boundaries remain: SignRepository, SignGenerator, AvatarRig.applyPose and SignClip v1. New metadata is optional for existing assets. Draft content retains notices; rejection prevents use of the rejected asset/rule rather than promoting it through a separate path.

## Prior local checks (2026-10-31)

- Backend: `cd backend; python -m pytest -q` — **184 passed**, one upstream Starlette/AnyIO deprecation warning. Used the project `.venv`; Windows asyncio initialization required running tests outside the sandbox.
- Frontend: `cd frontend; npm test -- --run` — **50 passed** across seven test files.
- Frontend: `npm run build` — TypeScript and Vite production build passed.
- Root: `python backend/tools/validate_signs.py` — passed metadata/file-reference checks. This does not certify ISL correctness or grant licensing permissions.
- Root: `python eval/run_eval.py` — expected **exit 2**, `NO_VERIFIED_ROWS`; no accuracy or linguistic-quality scores produced.
- Local runtime: Python 3.11.8, Node 24.13.0. Optional imageio-ffmpeg test binary installed; production FFmpeg/FFprobe remain configurable separately.

The CI software-check job runs tests, build and validation. Its independent evaluation-readiness job reports exit 2 (NO_VERIFIED_ROWS) as informational and succeeds without scores; every other nonzero exit still fails. A green software job must never be represented as a successful signer evaluation.

The default model is `claude-sonnet-5-5`, checked against the [official Anthropic model overview](https://platform.claude.com/docs/en/models/overview). Syntax validation cannot establish account-specific availability; use the documented optional model checker with an authorized key. No claim is made that the former default was invalid.

## Human input still required

1. **Licensed recordings and consent:** select the dataset/reference, obtain any access agreement and permission for the intended redistribution/use, and record signer consent/provenance. Dataset terms and unresolved checks are in `LICENSES.md`. No restricted corpus was downloaded or bundled.
2. **Sign/alphabet verification:** the registry still contains demo assets (see `python backend/tools/repo_stats.py` for current counts). Supply a licensed five-video ingestion sample, review converted quality, and supply/review the missing alphabet assets reported by `repo_stats.py`. Placeholder motion must not be treated as the ISL alphabet.
3. **Grammar/NMM content:** Deaf ISL signers and linguists must review the draft rules and author 20–50 sourced examples. Word-order operators, static marker channels and symbolic pronoun labels do not establish valid ISL grammar or spatial indexing.
4. **Evaluation:** replace the three explicitly marked placeholder rows with reviewer-approved English/gloss/NMM examples. Decide dialect, tokenization, acceptable alternate translations and comprehension criteria before interpreting exact-match metrics. The explicit `FS:` rate does not measure demo spelling that happens only in the browser.
5. **Expressiveness and quality:** classifiers, role shift, agreement and discourse-dependent signing-space references are not validated or fully represented. Monocular conversion has depth/orientation/occlusion limitations and limited facial information. Interpolation requires human checks for hand contact, collisions and comprehensibility.

No deployment, remote CI run or Git commit was performed. The engineering workflows are ready for those human inputs; recording verification, licensing approval and native-signer evaluation remain outstanding rather than being simulated.

## Repository hygiene, backend hardening and deployment update (2026-11-02)

The user authorized editing this supplied folder without commits because it has
no `.git` directory. No push was made. A reference search of the repo, `.github`,
Compose and docs found no references to the stale nested project outside itself;
the duplicate was removed from disk (95 files including hidden files in this
supplied copy). `git rm` is unavailable in this folder.

Runtime dependencies now exclude test tools; `requirements-dev.txt` includes
runtime requirements, pytest, coverage and Ruff. The required `tests` job retains
its stable name and gates on a Python 3.11/3.12 backend matrix. It uses Python
3.12 and Node 22, caches dependencies, runs npm ci,
TypeScript and Ruff, and prints pytest coverage in the summary. Evaluation exit
2 is informational, never a claim of signer evaluation. Other evaluator failures
remain failures. Docker CI builds both images and polls backend health.

Validated CORS origins, per-IP token buckets, export token/length caps and a
nonblocking export semaphore protect backend resources. Cleanup runs at startup
and every ten minutes, preserving `.gitkeep`. Public assets are restricted to
referenced clips/videos; `/api/alphabet` exposes only public provenance and
excludes rejected entries. The frontend uses that endpoint. Sequence building
runs in a worker thread; grammar/marker/example parsing caches reload by mtime.
The compatibility boundaries and existing response shapes remain intact.

Deployment targets Python 3.12/Node 22. The backend runs without root, retains
FFmpeg/WordNet and provides a healthcheck. nginx serves the production frontend
and proxies API/WebSockets/assets; a separate Compose override retains Vite.
Sign assets and generated exports persist through rebuilds. Make commands cover
tests, lint and Docker development. No real API or network calls occur in tests.

TODO (maintainer): run the authored Docker build/health checks on a Docker-enabled
host and run CI remotely on the pinned Python 3.12/Node 22 toolchains. The Docker CLI is
unavailable in the supplied environment; its available Python is 3.11.8 and
Node is 24.13.0. Confirm the stable required `tests` check in branch protection. Existing
licensing, recordings, signer review, grammar content and evaluation TODOs above
remain unchanged; no human content has been fabricated.

### Current local verification

- Backend: `python -m pytest -q --cov=. --cov-report=term-missing` — **227 passed**,
  one upstream Starlette/AnyIO deprecation warning. Tests ran outside the Windows
  sandbox because its asyncio initialization stalls. No tests skipped.
- Coverage: **93%** for backend source/tools, excluding test files; reported with
  `python -m coverage report --rcfile=../pyproject.toml`. CI uses this same config
  with `--cov-config=../pyproject.toml` and includes the report in the job summary.
- Frontend: `npm test` — **51 passed** in eight files; `npx tsc --noEmit` and
  `npm run build` passed.
- Ruff: `python -m ruff check .` and `python -m ruff format --check .` passed
  (52 Python files). Only flagged formatting/import/style issues were cleaned up;
  evaluator source-tree bootstrap imports retain explained E402 exceptions.
- Asset metadata/file validation passed. Evaluator still returns exit 2,
  `NO_VERIFIED_ROWS`, without scores.
- Workflow/Compose YAML parsed successfully. Actual readiness shell branches
  (exit 0, 1, 2, 7) and stable required-check gating (success, failure, cancelled,
  skipped matrix outcomes) passed with mocked evaluators using local Git Bash.
- Docker image builds and container health/proxy smoke checks remain unrun locally
  because the Docker CLI is unavailable. The authored CI job performs both image
  builds and backend HTTP health polling; remote CI has not been run or pushed.

## English handling, vocabulary measurement and SDK update

All edits remain in the explicitly requested workspace folder; no Git repository
was initialized, no commits created and nothing pushed. English filters and
WordNet heuristics make no ISL grammar claims. The new enabled drop-word rule is
unverified and repository matches still win. Additive FS reason/lemma diagnostics
reach REST, WebSocket metadata and sequence items. Optional synonyms/hypernyms are
off by default, exclude potential names/capitalized unknowns, and disclose meaning
drift. Coverage tooling and 60 English-only domain sentences measure local
repository gaps and report them to CI without a key or model call.

The official Anthropic SDK is pinned at 0.75.0. A shared lifecycle-managed async
client handles configured timeout/retries; forced emit_gloss tool output retains
independent parsing/vocabulary checks. Code ordering is the default and reports
only applied operations; model ordering remains available with unverified notices.
Both paths use the common marker stage. Stable prompt blocks request prompt caching
and log usage counts at DEBUG, without error bodies/keys. A bounded response
LRU/TTL cache keys on normalized input, repository/vocabulary, rule/example
mtimes, model, ordering and prompt settings. It stores no failed calls/fallbacks.

Tests block construction of a real SDK client unless explicitly replaced by a
fake. New tests cover filters and precedence, FS diagnostics, synonyms off/on and
names, local report files/errors, tool schema/forcing, timeout/429/malformed
fallback, secret-free logs, client lifecycle, ordering/marker parity and cache
hits, copies, TTL, eviction, disabling and invalidation. Existing parser and
vocabulary tests remain, adapted to fake SDK responses.

TODO (maintainer): validate real model access, tool support and prompt-cache
eligibility/savings using an authorized backend-only key. No live paid call or
model-quality claim was made. All earlier licence, licensed-recording, signer
review, grammar-example and evaluation prerequisites remain outstanding.

### Verification for the English/SDK update

- Backend: **279 passed**, one upstream Starlette/AnyIO deprecation warning;
  **93% coverage**, excluding test files. The full pytest suite ran with coverage
  outside the Windows sandbox; test model interactions used fake SDK clients only.
- Frontend: **51 passed**; `npx tsc --noEmit` and production build passed.
- Ruff lint and format checks passed for 57 Python files; pip dependency checks
  found no broken requirements. Sign metadata/file-reference validation passed.
- `eval/reports/english_coverage.json` and `.md`: **60 sentences**, **159 FS tokens /
  269 emitted tokens (59.1%)**, **0 measurement errors**, synonym fallback disabled.
  This is repository coverage only, not a linguistic evaluation or accuracy claim.
  BOUGHT records `lemma_tried=buy`; AND/FOR are filtered only when unmatched.
- New code paths preserve the extension seams and existing response fields;
  diagnostic fields are additive. No frontend behaviour was changed.
- Remote CI, Docker/pinned-runtime checks and authorized live SDK/model/cache
  validation were not performed locally. The available local runtimes remain
  Python 3.11.8 and Node 24.13.0; CI targets Python 3.11/3.12 and Node 22.
