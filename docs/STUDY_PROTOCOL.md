# Signer review and comprehension-study protocol

**Scaffold only: no participants or human judgements have been generated.** The
example packet uses actual deterministic pipeline output for five committed
sentences, one per domain. Its signs, expressions and interpolation are demo /
NOT verified ISL. Synthetic attestations appear only in software-test fixtures.

## Consent and reference review

Recruit and compensate consenting Deaf signers familiar with the target variety;
involve an ISL linguist in annotation design. Record dialect, experience,
accessibility needs, consent, withdrawal and retention arrangements privately.
Use study pseudonyms (R01, R02, ...) in sheets; do not publish names, contact details,
evidence recordings or private correspondence. Attribution records attestation;
it is not identity authentication, linguistic certification or licence approval.

1. Freeze the sentence batch and configuration. Export with:
   `python eval/tools/make_review_sheet.py --sentences batch.txt --packet-dir eval/private/packet`.
   Existing packets are never overwritten. The sheet includes source text,
   English intermediate, actual glosses/notices and two actual SVG samples per
   sign (normalized times 0.25 and 0.75).
2. Review independently before discussing responses. SVGRenderer projects the
   actual procedural rig and merged/sampled clips; shading differs from WebGL.
   Inspect full motion in the pinned app/source clips before judging temporal
   NMM. Frame strips cannot establish timing, scope, fluency or comprehension.
3. Complete `responses.csv`: `gloss_acceptable` and `nmm_correct` are
   yes/no/uncertain. Comprehension self-report is 1 cannot understand, 2 mostly
   unclear, 3 partly clear, 4 mostly clear, 5 fully clear. Record omissions,
   wrong signs, order/scope issues and dialect variants in comments.
4. Optionally supply a corrected `reviewed_gloss`, `acceptable_alternatives`
   separated by `|`, and `expected_nmm`: JSON list with one numeric object per
   reference gloss. `{}` means explicitly no expected numeric channels, not a
   substitute for missing review. Reference correctness and stimulus acceptability
   are different judgements: a corrected reference may be signed off even when
   the generated stimulus was rated unacceptable.
5. Observations remain in review. Only `decision=verified`, `signed_off=yes`,
   named attribution, private evidence and a nonempty aligned reference promote
   an evaluation row. `rejected` demotes it to unverified. No import promotes
   any sign, alphabet, clip or grammar rule; asset reviews remain separate.

```sh
python eval/tools/import_review_sheet.py eval/private/packet/responses.csv --packet eval/private/packet --output eval/private/reviewed.jsonl --reviewer-id R01 --reviewer "Consented reviewer name" --evidence "private attestation reference"
python eval/run_eval.py --testset eval/private/reviewed.jsonl --output eval/private/scores.json
```

These are operator examples, not fabricated people or judgements. Names/evidence
go to gitignored `*.identities.private.json`; row histories contain pseudonyms,
evidence hashes and UTC timestamps. Protect the directory with OS permissions,
keep the identity key under restricted access, and inspect any public derivative
manually: source text/comments themselves may be sensitive. Aggregate metric
summaries omit reviewer identities.

Manifest/checksum bind source code, configuration/data, canonical testset,
referenced assets, rendered strips and HTML. Changed sources, renders, manifest
or stimulus hashes are refused. Imports use a writer lock and atomic JSONL
replacement; an output receipt detects external changes to an existing target.
Duplicate ratings by one reviewer are refused; preserve originals and explicitly
adjudicate/re-export rather than silently replacing them. Hashes detect stale
edits, not malicious forgery. An export without its final checksum is incomplete.
Legacy plain CSV conversion is drafting only and never verifies from a name alone.
Existing asset review tools retain their stale-export/provenance/demo-refusal rules.

## Blinded comprehension study scaffold

```sh
python eval/study.py --packet eval/private/packet --output eval/private/study --n 12 --reviewers 3 --overlap 2 --seed 20261103
```

N must not exceed packet size. Seeded sampling is without replacement. Every item
is assigned to exactly `overlap` distinct reviewers, loads are balanced by rotation,
and each reviewer's presentation order is shuffled independently. Outputs include
the stimulus subset, per-reviewer HTML, BLANK response templates and `design.json`.
The bundled example uses N=5, R=3, overlap=2. No judgement is prefilled.

The generated HTML is a **blinded still-frame pilot**: gloss/source hints are
removed. It tests accessibility and still-frame interpretation only. Before a
signing-comprehension claim, replace frames with complete timed signer-approved
video/animation stimuli and freeze their hashes. Do not measure comprehension
from the reference-review sheet, where English/gloss answers are visible. Use
separate participants or counterbalanced lists to avoid answer exposure. Counterbalance
NMM on/off versions if using a repeated-measures design.

Preregister recruitment, sample size/power, dialect strata, exclusions, trial order,
scoring rubric, consent, compensation and primary endpoints before collecting data.
Collect free `meaning_response` before showing a reference, then the 1–5 rating.
Independent blinded humans score meaning using a separately agreed rubric; the
scaffold does not automatically mark answers correct. Record dropout/missingness
rather than imputing ratings. Pilot and lock the design before the main study.
No power, generalization or real comprehension result is claimed by the example.

## Metrics for the methods section

Only attributed, non-placeholder verified rows are scored. With none, the evaluator
keeps exit 2 / `NO_VERIFIED_ROWS` and produces no new scores. Exact sequence match
accepts annotated alternatives. Corpus WER sums edits against the reference with
minimum normalized distance, divided by total selected-reference length. Token
accuracy is `1-WER` (can be negative with many insertions). **Gloss accuracy is not
comprehension accuracy.** Numeric NMM match covers only configured channels.

Content coverage counts English token occurrences after an explicit function-word
filter, or reviewer-supplied `content_words`. It is a heuristic, not a POS analysis.
A word is covered only if all its deterministic lookup outputs are repository
signs. Demo signs count; verified non-demo asset coverage is reported separately.
FS rates count explicit gloss tokens, not rendered characters.

Agreement uses independent signed ratings on verified items: unweighted pairwise
Cohen kappa and fixed-rater-count Fleiss kappa. Duplicate raters are rejected;
missing/unsigned ratings are excluded. Degenerate/undefined kappa is null with a
reason. Fleiss uses the modal number of raters per item and reports excluded
different-size/incomplete items. Cohen uses complete overlaps. Likert values are
nominal categories here, not interval measurements. Preserve pre-adjudication
ratings; do not replace disagreements with consensus before computing agreement.
Report sample sizes, categories, exclusions and missingness with kappa. No
confidence interval or reliability claim is manufactured by this software.

Arithmetic uses the standard observed/chance-agreement formulations documented
in the [statsmodels inter-rater implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/inter_rater.html).
It is implemented locally with hand-counted synthetic tests, without adding a
statsmodels runtime dependency.

Label paper results by reviewed sample, dialect, reviewer pool, stimulus mode and
configuration. Gloss agreement, lexical coverage, rendering and comprehension are
distinct endpoints; current figures/ablations establish no verified ISL accuracy,
naturalness or signer comprehension.
