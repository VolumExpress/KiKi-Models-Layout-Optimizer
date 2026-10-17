# Universal Family Editor — four plate pilot (PR #7)

## The user workflow (no manual JSON)

1. Install the portable build of PR #7; keep a backup of `workspace` and `presets`.
2. Open a **copy** of P01/P03/P10/P11 in Illustrator, select the plate artwork, and click **Export selection**.
3. In `Family organization` choose **Semantic order · editor**. The panel sets `Rows` and `0°`; choose `Uniform` or `Dense`.
4. Calculate once. Expand **Family editor** below the family review. The plugin now shows **every** family, including singletons, with a vector thumbnail and observed sizes.
5. Edit the family labels, category (`roman`, `gothic`, `chapter`, `role`, `carrier`, `other`), optional numeral and relative priority. Use ↑/↓ to move rows; explicitly confirm only after visually verifying.
6. Calculate **again** after changes: the previous result is blocked from Apply. Inspect `preview_test.svg`, the report/warnings and the source contours on the Illustrator **copy** before applying.

The editor stores a versioned internal `family_plan.json` in its own plate workspace **automatically**. It is an implementation detail, not an authorable user input. Saved presets hold the UI mode, never the symbol mapping.

A previous P11 `semantic_order.json` in that workspace is automatically imported once when no newer plan exists; it is not required for a newly exported plate.

## Important limitations of this first iteration

- Editing **order, labels, categories and numeric values** is included. Manual splitting or merging of mistaken geometric families is **not yet implemented**. Inspect the detected family membership and correct the source or detection settings where needed.
- Metadata are **not written into .ai** in this PR. The sidecar is private to the workspace and survives repeated calculations. Re-exporting with changed UUIDs may require reviewing labels.
- Numeric meaning is never guessed from vector geometry. Codes are used for *identity*, not inferred glyph values. Missing or provisional mappings are visibly flagged and must be checked.
- The first calculation before any plan exists is exploratory; it builds the family catalog. A second calculation applies explicitly sorted semantic families.
- For production, verify real Illustrator contours; the SVG is an approximation.
- Never silently relax the specified physical gap; if adaptive clearance is used, its actual value is reported and requires confirmation.

## Four-plate QA checklist

|Plate|Object count|Test emphasis|
|---|---:|---|
|P01 Ultramarines|62|Mixed code-based names, unidentified symbols, preservation of sizes|
|P03 Dark Angels|71|Compound Bezier geometry after P03 hotfix, valid UUIDs|
|P10 Roles & Honours|68|Keeping same emblem variants together, no Compact fallback without warning|
|P11 Numbers & Squads|114|I–XX, Gothic 1–10, carriers; migrate old P11 mapping if present|

Apply the same baseline to each: engraving, Uniform, `By silhouette`, `Rows`, `0°`, requested gap `4.5 mm`, margins `3 mm`, `8` trials, `60` seconds, seed `42`, adaptive gap on. Outline matching can be toggled *as a separate controlled comparison*; do not compare family counts across different matching settings.

Before applying: all source IDs/UUIDs accounted for, minimum verified contour distance `>=` the **actual** gap, no margin violations, no rotations, no shape or area changes, correct visible family structure. Compare the preview before/after confirming category/order. Return screenshot and `result_test.json`/report for each plate.

## Status

- Public regression tests use **synthetic data modeled on each domain**. No user source artwork is uploaded.
- Structural source audits on the four private exports confirmed 62/71/68/114 objects respectively with unique non-empty UUIDs.
- A Windows Illustrator pass on all four real copies is necessary before merging PR #7.
