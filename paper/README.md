# Reproducible engineering artifacts

These artifacts measure the real offline lexical pipeline and project its actual
procedural avatar. They are **NOT verified ISL accuracy, comprehension or native
coarticulation results**. No human judgements are bundled.

Setup (Python 3.11.8 and Node 24.13.0 used for these artifacts):

```sh
python -m pip install -r backend/requirements.txt -r paper/requirements.txt
python -m nltk.downloader wordnet
npm ci --prefix frontend
```

One-command reproduction, with the project Python environment active:

```sh
python eval/reproduce.py
```

Outputs: three coverage reports, the 24-cell offline ablation, architecture and
coverage SVG/PNG figures, an actual response JSON and SVG expression comparison,
a blank five-domain reviewer packet, blank overlapping study scaffold and version/
seed record. Files go to `paper/generated` and `eval/reports`. Unchanged review
packets are reused after validation, never overwritten. If sources changed, use
a fresh `--output` directory and preserve old snapshots/returned human forms.

`eval/reports/ablation.md` covers code/model ordering, synonym fallback off/on,
real deterministic mock processing versus explicitly **simulated API transport**,
and en/hi/kn. The transport executes repository lookup in input order and the demo
glossary. It makes no live-model calls and supplies no invented model numbers.
Mock ignores LLM_ORDERING. Simulated 'model' ordering is an input-order fixture,
not model reasoning or an independent linguistic algorithm. Do not describe these
cells as Claude results. FS rates are insensitive to permutations.

All cells retain `NO_VERIFIED_ROWS` while the canonical testset is placeholders.
Synthetic unit fixtures never enter publication data. Seed: 20261103. Versions are
pinned in backend requirements, frontend lockfile and paper requirements. The
environment record includes Python/Node/package versions, configured-but-not-called
model ID and WordNet ZIP hash. Source/data hashes accompany the table. OS/fonts
can change image bytes: compare numbers and environments, not cross-platform byte
identity. CI runs a separate informational offline-ablation job and uploads its table.

Separate figure commands:

```sh
python paper/figures.py --reports eval/reports --output paper/generated
node paper/render_avatar.mjs --input paper/generated/expression_response.json --output paper/generated/expressions.svg
```

`generated/captions.md` states what every figure measures and what is unverified.
Standard Three SVGRenderer projects the actual AvatarRig/mergeNmm/pose geometry
using a minimal SVG DOM adapter and deterministic sampling. It is not AI artwork
or a photorealistic signer. Expression figures use a head crop; review strips use
the body framing. No idle/random motion is injected. Still images cannot validate
motion timing; video-only assets must also be viewed in their original video form.

See [the signer/study protocol](../docs/STUDY_PROTOCOL.md). The generated study is
only a blinded still-frame pilot; full-motion, consented signer-approved stimuli
and a preregistered design are required for a signing-comprehension study.
