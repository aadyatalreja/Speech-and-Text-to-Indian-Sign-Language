# Implementation report

Checked locally on 2026-10-31. Tasks 1–11 have their software implementation in place. Human-authored linguistic content and licensed recordings remain pending where described below; this is an experimental system, not validated ISL translation.

## Task inventory

Paths below are relative to the project root. This is an implementation inventory, not a Git diff: this supplied folder has no `.git` directory, so per-task commits could not be created.

| Task | Implementation and principal files | Verification |
| --- | --- | --- |
| 1. Metadata/repository | `backend/models/sign.py`, `backend/services/sign_repository.py`, `backend/data/signs/signs.json`, `backend/tools/validate_signs.py`: optional provenance, aliases, lemmas, categories and review metadata; normalized lookup and validation. | `test_sign_repository.py`, `test_validate_signs.py`; existing registry loads and validates. |
| 2. English coverage | `backend/services/english_service.py`, `gloss_service.py`, requirements: WordNet lemmatization, repository lookup before stop-word removal, contractions, numbers and explicit `FS:` fallback. WordNet was chosen for its small dependency/model footprint. | `test_english_service.py`, `test_translation.py`: inflections, polite vocabulary, proper names and digits. |
| 3. Constrained vocabulary | `backend/services/vocabulary_service.py`, `llm_service.py`: allowed vocabulary, deterministic shortlist for large registries, alias resolution and output postvalidation. | `test_vocabulary.py`, `test_translation.py`: invented output becomes explicit fingerspelling. No live paid model call was made. |
| 4. Structured gloss/NMM | Backend models, `marker_service.py`, `llm_service.py`, translation API; `frontend/src/avatar/nmm.ts`, avatar canvas and lab: structured gloss and sentence intent, backward-compatible flat response, configured marker propagation. | `test_markers.py`, API/translation tests, `nmm.test.ts`; unverified marker rules remain disabled. |
| 5. Grammar/review process | `backend/services/grammar_service.py`, `backend/data/grammar/isl_rules.yaml`, `examples.jsonl`, `docs/ISL_GRAMMAR_REVIEW.md`: editable operators, provenance/notices and verified-only prompt examples. | `test_grammar.py`, marker/translation tests. No fabricated 20–50 examples were supplied; the examples file awaits signer review. |
| 6. Alphabet/digits | `backend/models/alphabet.py`, `backend/data/signs/alphabet/`, `frontend/src/avatar/alphabetAssets.ts`, `alphabet.ts`, `library.ts`: asset-driven letter/digit composition and honest missing-asset fallback. | `test_alphabet.py`, `alphabetAssets.test.ts`; all 36 letters/digits remain explicitly missing pending licensed references. |
| 7. Ingestion/QA | `backend/tools/bulk_import.py`, manifest/permission templates, converter adapter, `backend/requirements-ingest.txt`, `docs/INGESTION.md`, `LICENSES.md`: resumable import, QA, provenance, locking and verified-entry protection. | `test_bulk_import.py`, `test_mediapipe_to_clip.py`, fixture landmark tests. A real licensed five-video MediaPipe run remains pending supplied recordings/permission. |
| 8. Video playback/export | `frontend/src/services/videoPlayback.ts`, player/UI integration, `backend/services/video_service.py`, video API, `docs/VIDEO_PLAYBACK.md`: media-ended chaining, mode selection, mixed availability notices and normalized FFmpeg export. | `videoPlayback.test.ts`, `test_video_service.py`, API tests, real FFmpeg synthetic-color integration and browser smoke checks. Synthetic clips are not sign recordings. |
| 9. Timing/transitions | `backend/services/timing_service.py`, `sequence_service.py`, sign models/config; `frontend/src/services/timelinePlayback.ts`, `hooks/useSignPlayer.ts`, avatar pose/canvas/library, App and lab; `docs/TIMING.md`: actual asset durations, configurable gaps, elapsed-time playback and previous-end-pose blending. | `test_timing.py`, `timelinePlayback.test.ts`, `transitions.test.ts`; lab visually checked at start/midpoint of a transition between demo clips. Linguistic motion quality still needs signers. |
| 10. Evaluation/review | `eval/run_eval.py`, `isl_testset.jsonl`, `backend/tools/review_assets.py`, review metadata/filtering across loaders, `.github/workflows/checks.yml`, `docs/EVALUATION_AND_REVIEW.md`: verified-only metrics and offline export/apply decisions with evidence, audit history, stale-state checks and rejection handling. | `test_evaluation.py`, `test_review_assets.py`. Placeholder-only evaluator exits 2 without scores. CI workflow is authored but has not run remotely. |
| 11. Configuration/docs | `backend/config.py`, `backend/tools/check_model.py`, requirements, `.env.example`, `docker-compose.yml`, `README.md`, UI wording/title: environment validation, documented defaults, optional authenticated model lookup and honest limitations. | `test_config.py`, mocked model lookup tests, production build. No real API key/model-access check was performed. |

The compatibility boundaries remain: SignRepository, SignGenerator, AvatarRig.applyPose and SignClip v1. New metadata is optional for existing assets. Draft content retains notices; rejection prevents use of the rejected asset/rule rather than promoting it through a separate path.

## Final local checks

- Backend: `cd backend; python -m pytest -q` — **184 passed**, one upstream Starlette/AnyIO deprecation warning. Used the project `.venv`; Windows asyncio initialization required running tests outside the sandbox.
- Frontend: `cd frontend; npm test -- --run` — **50 passed** across seven test files.
- Frontend: `npm run build` — TypeScript and Vite production build passed.
- Root: `python backend/tools/validate_signs.py` — passed metadata/file-reference checks. This does not certify ISL correctness or grant licensing permissions.
- Root: `python eval/run_eval.py` — expected **exit 2**, `NO_VERIFIED_ROWS`; no accuracy or linguistic-quality scores produced.
- Local runtime: Python 3.11.8, Node 24.13.0. Optional imageio-ffmpeg test binary installed; production FFmpeg/FFprobe remain configurable separately.

The CI software-check job runs tests, build and validation. Its independent evaluation-readiness job deliberately fails until verified evaluation rows exist. A green software job must never be represented as a successful signer evaluation.

The default model is `claude-sonnet-5-5`, checked against the [official Anthropic model overview](https://platform.claude.com/docs/en/models/overview). Syntax validation cannot establish account-specific availability; use the documented optional model checker with an authorized key. No claim is made that the former default was invalid.

## Human input still required

1. **Licensed recordings and consent:** select the dataset/reference, obtain any access agreement and permission for the intended redistribution/use, and record signer consent/provenance. Dataset terms and unresolved checks are in `LICENSES.md`. No restricted corpus was downloaded or bundled.
2. **Sign/alphabet verification:** the registry still contains 40 demo entries, with no verified real sign assets. Supply a licensed five-video ingestion sample, review converted quality, and supply/review all 26 letters and 10 digits. Placeholder motion must not be treated as the ISL alphabet.
3. **Grammar/NMM content:** Deaf ISL signers and linguists must review the draft rules and author 20–50 sourced examples. Word-order operators, static marker channels and symbolic pronoun labels do not establish valid ISL grammar or spatial indexing.
4. **Evaluation:** replace the three explicitly marked placeholder rows with reviewer-approved English/gloss/NMM examples. Decide dialect, tokenization, acceptable alternate translations and comprehension criteria before interpreting exact-match metrics. The explicit `FS:` rate does not measure demo spelling that happens only in the browser.
5. **Expressiveness and quality:** classifiers, role shift, agreement and discourse-dependent signing-space references are not validated or fully represented. Monocular conversion has depth/orientation/occlusion limitations and limited facial information. Interpolation requires human checks for hand contact, collisions and comprehensibility.

No deployment, remote CI run or Git commit was performed. The engineering workflows are ready for those human inputs; recording verification, licensing approval and native-signer evaluation remain outstanding rather than being simulated.
