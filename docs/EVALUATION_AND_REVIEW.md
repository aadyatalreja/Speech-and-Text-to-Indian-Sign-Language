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

The `evaluation-readiness` CI job runs this command directly and deliberately
fails until genuine reviewed rows are supplied. Software tests/build have their
own job. Unit tests use explicitly synthetic review flags solely to validate
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
Restart the backend (cached repository), then reload the browser.

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
