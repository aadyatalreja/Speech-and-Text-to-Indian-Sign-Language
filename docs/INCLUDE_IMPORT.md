# Import locally supplied INCLUDE-style recordings

Use this workflow for authorized INCLUDE recordings. Check the exact archive
and record the applicable terms using LICENSES.md and INGESTION.md.

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

## Pronoun pilot source recordings

The pilot uses individual members from the original
[INCLUDE archive](https://zenodo.org/records/4010759). The
[archive metadata](https://zenodo.org/api/records/4010759) lists CC BY 4.0.
Credit Advaith Sridhar, Rohith Gandhi Ganesan, Pratyush Kumar, and Mitesh
Khapra, and the Deaf students at St. Louis School for the Deaf in Chennai.
The recorded motion was converted to landmarks and retargeted to the avatar.

| Gloss | Archive part | Original member |
| --- | --- | --- |
| I | Pronouns_1of2.zip | Pronouns/40. I/MVI_0013.MOV |
| YOU | Pronouns_1of2.zip | Pronouns/41. you/MVI_9888.MOV |
| HE | Pronouns_1of2.zip | Pronouns/42. he/MVI_0018.MOV |
| WE | Pronouns_2of2.zip | Pronouns/45. we/MVI_9973.MOV |
| THEY | Pronouns_2of2.zip | Pronouns/47. they/MVI_0035.MOV |

The source labels apply to these recordings. The archives do not contain a
separate ME label. The five pilot recordings are kept in an ignored local
folder. Avatar clips and landmark files carry source attribution. A signer
review is required to evaluate the retargeted movement.

## Expanded vocabulary source recordings

These clips use the same CC BY 4.0 source and conversion process as the
pronoun pilot above. Open the avatar lab and choose **Imported signer clips**
to preview the animations. The converted clips still require signer review.

| Gloss | Archive part | Original member |
| --- | --- | --- |
| AFTERNOON | Days_and_Time_3of3.zip | Days_and_Time/83. Afternoon/MVI_9191.MP4 |
| BANK | Places_4of4.zip | Places/35. Bank/MVI_3501.MOV |
| BATHROOM | Home_2of4.zip | Home/32. Bathroom/MVI_9025.MP4 |
| BEDROOM | Home_1of4.zip | Home/30. Bedroom/MVI_4896.MOV |
| BLACK | Colours_2of2.zip | Colours/54. Black/MVI_5060.MOV |
| BLUE | Colours_1of2.zip | Colours/49. Blue/MVI_5045.MOV |
| BOOK | Home_2of4.zip | Home/37. Book/MVI_9041.MP4 |
| CHAIR | Home_1of4.zip | Home/25. Chair/MVI_9005.MP4 |
| CITY | Places_1of4.zip | Places/18. City/MVI_3592.MOV |
| EVENING | Days_and_Time_3of3.zip | Days_and_Time/84. Evening/MVI_5518.MOV |
| FRIDAY | Days_and_Time_1of3.zip | Days_and_Time/71. Friday/MVI_9155.MP4 |
| GREEN | Colours_1of2.zip | Colours/48. Green/MVI_5041.MOV |
| HOSPITAL | Places_3of4.zip | Places/30. Hospital/MVI_3639.MOV |
| HOUR | Days_and_Time_2of3.zip | Days_and_Time/79. Hour/MVI_9181.MP4 |
| KITCHEN | Home_2of4.zip | Home/31. Kitchen/MVI_8778.MP4 |
| LIBRARY | Places_3of4.zip | Places/29. Library/MVI_3479.MOV |
| MARKET | Places_3of4.zip | Places/32. Market/MVI_3489.MOV |
| MINUTE | Days_and_Time_2of3.zip | Days_and_Time/80. Minute/MVI_5501.MOV |
| MONDAY | Days_and_Time_1of3.zip | Days_and_Time/67. Monday/MVI_9144.MP4 |
| MONTH | Days_and_Time_2of3.zip | Days_and_Time/77. Month/MVI_9173.MP4 |
| OFFICE | Places_2of4.zip | Places/25. Office/MVI_3460.MOV |
| PARK | Places_2of4.zip | Places/27. Park/MVI_3630.MOV |
| PENCIL | Home_2of4.zip | Home/33. Pencil/MVI_9030.MP4 |
| RED | Colours_1of2.zip | Colours/47. Red/MVI_4207.MOV |
| RESTAURANT | Places_1of4.zip | Places/22. Restaurant/MVI_3607.MOV |
| SATURDAY | Days_and_Time_1of3.zip | Days_and_Time/72. Saturday/MVI_5027.MOV |
| SCHOOL | Places_2of4.zip | Places/24. School/MVI_3537.MOV |
| TODAY | Days_and_Time_1of3.zip | Days_and_Time/73. Today/MVI_5032.MOV |
| TOMORROW | Days_and_Time_2of3.zip | Days_and_Time/74. Tomorrow/MVI_5034.MOV |
| WHITE | Colours_2of2.zip | Colours/55. White/MVI_4216.MOV |
