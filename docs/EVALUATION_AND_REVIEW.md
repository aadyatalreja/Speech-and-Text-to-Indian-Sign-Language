# Evaluation and signer review tooling

No verified ISL evaluation rows are bundled. The three JSONL entries in
`eval/isl_testset.jsonl` are explicitly marked placeholders with empty expected
gloss/NMM lists. They are templates for collecting human content, not generated
English-to-ISL examples.

## Evaluation

```text
python eval/run_eval.py --testset eval/isl_testset.jsonl --output scores.json
```

Only `review_status: verified`, non-placeholder rows are scored. Verified rows
require reviewer attribution, a nonempty expected gloss, and one expected NMM
object per token. An empty `{}` means no expected configured numeric channels.
The output records engines/notices and reports exact gloss match, raw sequence
edit distance, edit distance/reference-token count, verified-real-asset coverage,
explicit FS rate, and per-sentence exact NMM match. Coverage excludes demos,
missing files, unverified/rejected assets, and FS tokens. FS rate measures
explicit sequence tokens, not browser-only fallback motions. NMM match compares
the configured numeric channel subset; it does not assess complete facial grammar.

**No verified rows: exit 2 with NO_VERIFIED_ROWS and no new scores.** Parse/setup
errors exit 1. Never interpret ignored placeholders as zero-quality samples or
report fixture metrics as ISL results. Existing output files are not regenerated
on failure; always inspect the exit code. Metrics require separate comprehension,
regional-variation, and native-signer evaluation before any linguistic claim.

The `evaluation-readiness` CI job reports exit 2 (`NO_VERIFIED_ROWS`) as
informational in the job summary and exits successfully without scores. All
other nonzero evaluator exits still fail the job. Software tests/build have
their own required `tests` job, gated on the backend version matrix. Unit tests use explicitly synthetic review flags solely to validate
arithmetic and gating; they do not contribute to the bundled test set.

## Export, review, apply

The review workflow is local JSON export; there is no public HTTP write API.
Export a snapshot before reviewing:

```text
python backend/tools/review_assets.py export review.json --kind sign --id HELLO
```

Use the gloss of an acquired asset in practice. The bundled HELLO is a demo and
cannot be verified; the example illustrates export syntax only.

Kinds: `sign` (repository gloss), `clip` (`clips/<name>.json`), `rule` (grammar/NMM
ID), `alphabet` (A–Z/0–9). `--root` selects a sign directory; `--grammar` selects
the YAML. Export refuses to overwrite an existing review file. The output
contains a snapshot, whole-document hash, and referenced asset hashes, with no
decision prefilled. Export is not sign-off.

Have a consenting Deaf ISL signer/linguist review the exact material/context and
edit `decision` to `verified` or `rejected`, `reviewer`, `comments`, and `evidence`.
Retain real attribution/consent and a reference to sign-off evidence. Do not
place private recordings or correspondence in public metadata. Then explicitly
apply the human decision:

```text
python backend/tools/review_assets.py apply review.json
```

The command refuses blank attribution/comments/evidence and stale snapshots or
changed referenced assets. It uses the same writer lock as ingestion and atomic
target-file replacement. Run while other editors are not modifying the same
files. Review fields/history are recorded with UTC timestamps and source hashes.
The backend reloads changed sign/alphabet metadata on the next request; reload the browser to refresh cached playback assets.

Verification refuses demos/missing assets, missing provenance, and unconfigured
rule placeholders. A verified sign review covers its referenced asset hashes.
Clip-only verification does not automatically promote a repository entry; review
that sign separately. A clip rejection demotes referencing entries and blocks
that clip. A sign rejection becomes an explicit spelling fallback. Alphabet
rejections keep missing-character fallback labels. Rule rejections disable only
the reviewed rule. Rejected decisions are recorded separately while
`review_status` stays `unverified`, preserving the existing three-status schema.
Re-enable a corrected reviewed rule explicitly after review; verification does
not silently enable previously disabled rules.

This is a record of human attestation, not identity authentication or legal
permission. Signer review does not replace licence approval, and review of one
asset/rule never verifies the full app. See [grammar review](ISL_GRAMMAR_REVIEW.md)
and [licence requirements](LICENSES.md).

## Reviewer sentence workflow

```text
python eval/tools/make_review_sheet.py --output review.csv
python eval/tools/import_review_sheet.py review.csv --output eval/isl_testset.jsonl
python eval/run_eval.py --output scores.json --markdown-output scores.md
python eval/run_eval.py --check --tolerance 0.01
```

A Deaf ISL signer fills reviewed_gloss with space-separated tokens, optional
acceptable_alternatives separated by `|`, nmm_notes, reviewer, signer_dialect and
comments. Empty glosses are rejected; only a nonempty reviewer marks a returned
row verified. Blank reviewers remain unverified; verification is never inferred
from the source or a plausible gloss. Intent labels are initially classified from
English punctuation/negation and should be checked in the JSONL. Free-text NMM
notes are preserved; empty numeric NMM objects do not claim numeric marker review.

JSON and Markdown report exact agreement with any accepted reference, token WER
against the reference with minimum normalized edit distance, fingerspelling,
lexical OOV (no repository lookup), and statement/question/negation breakdowns.
Asset coverage remains a separate metric. Below 20 verified rows the output warns
that numbers are unreliable. These scores measure agreement with these reviewers'
sentences, not general ISL quality, comprehension, dialect coverage or naturalness.

After human acceptance, copy the real report's gloss_exact_match and
gloss_word_error_rate into eval/baseline.json. Its initial null values deliberately
claim no accepted baseline. --check fails when exact match drops or WER rises by
more than the absolute --tolerance. CI keeps NO_VERIFIED_ROWS (exit 2) informational;
no scores are produced in that case. --fixture exercises built-in SYNTHETIC rows
only for software tests and must never be used in CI evaluation reporting or as
an accepted baseline.

## Experimental Indian-language input

Choose हिन्दी (hi-IN) or ಕನ್ನಡ (kn-IN) in the shared typing/speech language
selector. The Web Speech API remains the recognizer; support depends on the
browser/service. Typed Unicode text uses the same source_language request field.
For non-English input, the backend uses the existing Claude client to translate
into English, then sends only that intermediate text to gloss generation and
marker rules. Successful English translations share the configured bounded TTL
cache. The normal translation endpoint/WebSocket rate limit covers the complete
request, including this first step; SDK retries and timeouts remain those of M4.

Every such response carries “Machine-translated to English first; not verified.”
and english_text. The UI lets you edit the intermediate sentence and re-run it as
English. In mock mode a notice explains that non-English input needs
LLM_PROVIDER=api and treats the original as English. API failures also use the
original as English with an explicit failure notice. A fallback is not a successful
machine translation or linguistic verification. With API mode, source text is sent
to the configured Claude service; existing API data handling applies.

## Experimental wrong-sign reports and privacy

Each sign has a Report button. The dialog submits only gloss, nullable sign_id,
sentence, optional note (at most 300 characters) and client timestamp. No login,
account identifier or IP is included in the stored report. Sending is explicit;
opening/closing the dialog does not submit. Avoid entering personal information:
the sentence/note themselves are free text and may be sensitive.

POST /api/feedback returns 204 and appends a JSONL record to
backend/data/feedback/reports.jsonl, which is gitignored. File locking prevents
concurrent append/cap races. RATE_LIMIT_FEEDBACK_PER_MIN defaults to 5;
FEEDBACK_MAX_BYTES defaults to 5000000. Oversized fields are rejected; once the
file cap is reached writes return 507 and leave existing records intact. The rate
limiter uses transient process-memory peer keys; no peer/account data is written
into reports. Hosting access logs are a separate operator responsibility.

```text
python backend/tools/review_assets.py feedback list
python backend/tools/review_assets.py feedback list --file local/reports.jsonl
```

This read-only command groups counts by gloss/sign ID so a reviewer can prioritize.
Reports never alter review_status, clip files, assets or rules and are not review
decisions. A consenting Deaf ISL signer must use the separate existing export/apply
workflow to approve or reject assets. The operator should restrict access, choose
an appropriate retention period and manually remove/archive the report file when
needed; no automatic third-party upload or indefinite retention guarantee is added.
