# Sign asset licences and dataset access

Checked against the linked primary sources on **2026-10-31**. No third-party
dataset videos were downloaded or ingested by Task 7. Listing a source here is
not approval to copy it. Asset licences, access conditions, derivative pose
permissions, signer consent/attribution, and the intended use must all be checked
for the exact files acquired. Dataset/code licences must not be conflated.

| Source | Observed terms | Project decision |
| --- | --- | --- |
| [ISLRTC copyright policy](https://islrtc.nic.in/copyright-policy/) and its linked dictionary | The site requires DEPwD permission for reproduction and appropriate acknowledgment for references. Do not infer permission from public viewing or a YouTube link. | **Pending permission. Do not ingest or redistribute dictionary videos/derived clips without applicable authorization.** |
| [AI4Bharat INCLUDE dataset card](https://huggingface.co/datasets/ai4bharat/INCLUDE/blob/main/README.md) | Card lists CC BY 4.0; the Hugging Face files contain metadata and link to original videos. This is distinct from the [training code repository](https://github.com/AI4Bharat/INCLUDE). | **Candidate only.** Check original video archive terms, preserve attribution and modifications, and record rights for the exact files before import. No archive downloaded. |
| [Exploration Lab CISLR](https://huggingface.co/datasets/Exploration-Lab/CISLR) and [dataset card](https://huggingface.co/datasets/Exploration-Lab/CISLR/blob/main/README.md) | Metadata lists AFL 3.0; dataset access is gated and requires accepting access conditions/sharing account information. | **Pending access/terms review.** Do not treat the metadata licence alone as redistribution permission; the user must obtain access and retain the applicable agreement. No login or agreement accepted by this task. |
| [Exploration Lab iSign dataset card](https://huggingface.co/datasets/Exploration-Lab/iSign/blob/main/README.md) | Card lists CC BY-NC-SA 4.0, research/non-commercial use, and an access checkbox prohibiting further sharing/upload. | **Not approved for bundled playback redistribution.** The additional access conditions must be resolved with the owner before redistributing videos or derived clips; research access alone does not satisfy this importer's redistribution requirement. Sentence-level evaluation use requires its own terms review. |

INCLUDE is a candidate for isolated-sign ingestion; iSign is a candidate for
sentence-level research evaluation subject to its restrictions. None is claimed
to solve native-signer review or regional coverage. A technically successful
conversion is not linguistic verification.

## Required import permissions record

`bulk_import.py` requires `--permissions <json>` and `--intended-use <text>`.
The JSON is keyed by the **exact** source value in the CSV. Each record needs:

- `licence`: exact match with the manifest;
- `intended_use`: exact match with the command's intended use;
- `allow_processing: true` and `allow_redistribution: true`: confirmed rights
  covering the original video and derived clips/landmarks for this use;
- `reviewer`: person who checked those rights;
- `evidence`: licence URL or permission reference, with any limits recorded.

The supplied example has both permissions **false** and cannot authorize an
import. Do not toggle flags to bypass unavailable rights. Unknown/restrictive
sources need actual permission evidence. Human attestation is recorded, not
automatically legally verified. Evidence references are included in sign
metadata served by the app; do not embed private correspondence or personal
documents. The importer never accepts dataset agreements or downloads data.

All imported signs and clips receive `review_status: unverified`, even if the
source dataset is authoritative. Rights review and Deaf signer review are
separate processes. `--force` allows replacing a verified entry, resets it to
unverified, and does **not** bypass the permissions check.

## Tooling dependencies

Video extraction uses an optional, separately pinned legacy MediaPipe Holistic
adapter. [Google's legacy solution documentation](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/holistic.md)
describes its API and legacy status; [MediaPipe 0.10.21](https://pypi.org/project/mediapipe/0.10.21/)
is pinned for that interface rather than assuming the latest package has
`mp.solutions`. A version lacking that API produces an actionable error.
Dependency licences do not confer rights to any video dataset. The normal
backend and CI fixture path do not require MediaPipe or OpenCV.
