# ISL grammar review workflow

**Status: draft / unverified. No native-signer-reviewed ISL rules or example
translations are supplied.** The current ordering and phrase mappings are legacy
engine demos. They must not be used to teach or certify ISL.

## Current status

| Item | Status | Runtime behavior | Required review |
| --- | --- | --- | --- |
| `legacy_function_word_filter` | Unverified | Enabled; English words dropped only after sign lookup fails | Whether/when dropping preserves meaning |
| `legacy_phrase_1`–`legacy_phrase_7` | Unverified | Enabled exact demo mappings; labeled per mapping | Meaning, word order, regional/register variation |
| `legacy_category_order` | Unverified | Enabled demo category sorting | Order, scope, contextual exceptions |
| `isl_*_pending_review` (8 entries) | Unverified / pending | Disabled; cannot be enabled as placeholders | Word order, question/negation position, time-first, topic/comment, copula/articles, plural repetition, pronoun indexing |
| Question/negation NMM templates | Unverified / pending | Disabled with no pose values | Form, timing, span, interaction with lexical signs |
| `examples.jsonl` | Empty | No few-shot examples included | Collect 20–50 reviewed translations; do not generate substitute ISL pairs |

## Review process

1. Recruit Deaf ISL signers and an ISL linguist where available. Agree on the
   intended regional variety, audience, register, and compensation. Obtain
   consent before retaining or redistributing review recordings and attribution.
2. Supply the English sentence, proposed gloss sequence, intended meaning, real
   sign assets when available, and the system's current limitations. A gloss
   alone cannot establish the correctness of a signed utterance. Separate
   grammar review from asset/license review and avatar motion quality.
3. Review one rule or example at a time. Record acceptable contexts, ambiguity,
   counterexamples, reference citations, dialect differences, and NMM scope.
   Keep unsupported cases unverified. Conflicting reviews require resolution,
   not a majority label invented by the software.
4. Edit `backend/data/grammar/isl_rules.yaml`. For a supported grammar operation,
   supply its parameters, a real `source`, the consenting `reviewer`, and
   `review_status: in_review`. Test with fixture inputs and native-signer feedback.
   Pending rules must be replaced with a supported operation before activation.
5. Only after explicit sign-off, set that grammar rule's `review_status` to
   `verified`. A nonblank reviewer is required. Never bulk-mark unrelated rules.
   For NMM rules also set `needs_signer_review: false`; see the Task 4 schema.
   Grammar review does not verify any sign asset or make the full app validated.
6. Add the reviewed example to `examples.jsonl` using the schema below. Aim for
   20–50 varied examples covering accepted rules and their boundaries. Keep
   drafts marked `unverified` or `in_review`; they are excluded from prompts.
7. Run backend/frontend tests and sign validation. Check API notices, the
   per-rule `grammar_rules` list, and avatar/lab behavior. Disabling a rule takes
   effect on subsequent translations without restart. Keep a dated review record.

## Review record template

```text
Rule/example ID:
Date and revision:
English input and intended meaning:
Proposed gloss (supplied by reviewer):
NMM description, channels, and span (if representable):
ISL variety / register / audience:
Reference source and exact page/timecode:
Reviewer attribution and consent:
Decision: unverified / in_review / verified
Accepted contexts:
Counterexamples / exclusions:
Corrections requested:
Signer sign-off evidence location (access controlled if needed):
Asset licence/source review (separate from grammar review):
```

Do not paste personal review recordings into the repository without permission.
No recording or human attribution is bundled by this task.

## Editable operations

Grammar rules live in the YAML `grammar` list; Task 4's NMM rules remain in
`rules`. Each grammar rule has `id`, `source`, `review_status`, `reviewer`,
`enabled`, and `operation`. Unverified rules may run only as disclosed demos.
Supported operations are implementation mechanisms, not claims of ISL grammar:

| Operation | Parameters | Meaning in this engine |
| --- | --- | --- |
| `drop_words` | `words` | English lexical filtering after repository lookup fails; cannot discard a known sign |
| `phrase` | `english`, `gloss`, optional `intent` | Exact tokenized English match; requires repository glosses and cannot silently discard input tokens; a match stops later ordering |
| `order_categories` | `categories`, with exactly one `rest` | Stable ordering by repository English categories; unknown categories/FS go into `rest` |
| `move_category` | `category`, `position: start/end` | Stable movement of matching tokens, e.g. a reviewed time/question/negation placement |
| `topic_first` | sentence metadata `topic` | Move a matching explicit topic gloss first; does not infer a topic |
| `repeat` | `category`, `count: 1..3` | Configured token repetition; optional `when_words` gates on supplied English words; does not infer an ISL plural rule |
| `pronoun_index` | `references: {gloss: referent_label}` | Annotate configured referents in `gloss_detail` and sequence metadata; no spatial coordinates or hand motion are invented |
| `pending` | review notes | Non-executable placeholder; rejected if enabled |

`when_words` optionally gates non-filter operations on an exact English token
(case insensitive). It supplies no automatic linguistic analysis. Rules run in
file order. No classifier, agreement, role shift, or signing-space implementation
is implied by symbolic reference labels. These limitations require future
representation work as well as signer input.

## Example file schema

Each nonblank line in `backend/data/grammar/examples.jsonl` is a JSON object:

```text
english: string supplied for review
gloss: list of canonical repository gloss strings or explicit FS:<WORD> tokens
nmm: optional numeric rig object {brow?, head?, mouth?}; default {}
reviewer: consenting reviewer's attribution, required when verified
review_status: unverified | in_review | verified
```

This is a schema template, not an English→ISL translation example. The file is
intentionally empty until real reviewed content is supplied. Do not fill it with
generated translations to meet the target count.

Only `verified` examples with a reviewer and vocabulary compatible with the
request are included in the API prompt, up to 50. Shortlisting can reduce the
number of usable examples. Draft examples never act as few-shot demonstrations.
Malformed records fail explicitly; absence of examples is allowed and disclosed.
Example NMM values do not bypass runtime YAML marker gating.

## Notices and scope

Mock responses list rules that matched or filtered input. Each draft influence
appears in `notice` as **Unverified grammar** and in UI/API `grammar_rules`.
Verifying one rule removes only that rule from the draft warning. Disabled and
unmatched rules do not acquire credit. API mode lists every active rule actually
included in the prompt, since exact model compliance cannot be proven, and keeps
an additional `llm_ordering_not_signer_reviewed` warning. Reviewed examples and
vocabulary constraints do not certify an LLM's generated translation.
