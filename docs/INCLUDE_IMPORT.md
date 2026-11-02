# Import locally supplied INCLUDE-style recordings

No download or real import is performed by this change. Dataset availability and
metadata licences alone do not grant permission; read LICENSES.md and INGESTION.md.

1. Place authorized local files at `local/include/category/word/video.mp4`. Keep
   the original terms, attribution and signer consent. Install the optional
   extraction environment described in INGESTION.md.
2. Preview and build the manifest (replace the quoted values with actual provenance):

   ```text
   python backend/tools/include_manifest.py local/include --licence "actual licence" --source "exact source" --signer-note "recorded signer attribution" --limit 5 --dry-run
   python backend/tools/include_manifest.py local/include --licence "actual licence" --source "exact source" --signer-note "recorded signer attribution" --limit 5 --output local/manifest.csv
   ```

   Columns exactly match import_manifest.example.csv, including optional empty
   landmarks_path. Uppercase folder words become underscore glosses. Sorted paths
   select one recording per gloss deterministically, including across categories.
   Inspect skipped variants and assign reviewer-chosen IDs manually if needed.
   Only separator spelling variants become aliases; no synonyms are invented.
3. Copy `backend/tools/import_permissions.example.json` to `local/permissions.json`
   (see LICENSES.md for its required fields). Fill the exact source key, licence,
   intended_use, processing/redistribution permissions, rights reviewer and public
   evidence reference based on actual permission. The default flags authorize nothing.
4. Run the import only after that rights review:

   ```text
   python backend/tools/bulk_import.py local/manifest.csv --permissions local/permissions.json --intended-use "actual approved intended use" --copy-video
   python backend/tools/validate_signs.py
   python backend/tools/repo_stats.py
   ```

5. Preview clips in `/lab.html`, review generated video exports, and follow
   EVALUATION_AND_REVIEW.md to export a review sheet with `review_assets.py`,
   obtain decisions and apply the returned decisions:

   ```text
   python backend/tools/review_assets.py export local/asset_review.json --kind sign --id YOUR_IMPORTED_GLOSS
   python backend/tools/review_assets.py apply local/asset_review.json
   ```

   Have the Deaf ISL signer fill the exported decisions before the apply command. The backend picks up changed
   registry metadata on the next request; refresh browser asset caches.

All imported entries are **unverified until a Deaf ISL signer approves them through
review_assets.py**. Technical QA, an import success, and a rights approval are not
linguistic verification. Keep recordings and signer review as separate human steps.
