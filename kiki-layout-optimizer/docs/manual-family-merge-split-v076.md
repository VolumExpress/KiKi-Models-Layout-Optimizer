# v0.7.x experimental — manual family merge / split (PR #8)

Manual regrouping is an opt-in extension of the integrated Family editor. It
never modifies paths or symbol dimensions in the Illustrator source.

## Review the current four-plate baseline

Before trying regrouping, the private workspace(2).rar passed independent
pairwise Shapely checks across **13,095 object pairs**:
P01 62/62, P03 71/71, P10 68/68, P11 114/114, all
requested/used gap 4.5 mm, no overlaps, all 3-mm margins respected.
This is export-geometry validation, **not** manufacturing sign-off.

## Trial on a COPY of P11

1. Back up `workspace` and `presets`; install the PR #8 test build.
2. Choose `Semantic order · editor`, Uniform, Rows, 0°, gap 4.5 mm, margins
   3 mm, 8 trials, 60 seconds, seed 42, adaptive gap on.
3. Export P11 unchanged if needed and calculate once. Open
   `Family editor`. Preserve previous reviewed metadata.
4. Select *both* Roman XIV rows (previous labels **Семейство 1** and
   **Семейство 22**, corresponding to 2 and 1 objects); click
   `Объединить выбранные семейства`.
5. Select *both* Roman XVI rows (**Семейство 2** and
   **Семейство 23**); merge likewise.
6. Both merged rows become *provisional*. Visually confirm each has three
   objects and the correct Roman value (XIV = 14, XVI = 16). Mark both
   Confirmed using their own checkbox. The app refuses to calculate if
   numeric merged rows remain unconfirmed.
7. Click Calculate and inspect `result_test.json`,
   `preview_test.svg`, the warnings and the editor family count. All 114
   UUIDs must be preserved, physical contours unchanged, gap >= actual
   setting, no overlaps or margins violated.
8. Separately test split on a harmless family in P01/P03/P10. Choose some
   member checkboxes in `Разделить`, then `Отделить` and calculate.
   Finally use `Сбросить ручные группы` and recalculate to return to
   automatic families.

**Do not Apply to master .ai** while testing.

## Safety contract

- The stored `family_plan.json` is internal to the workspace and includes
  `manual_grouping=true` after an explicit user merge/split.
- A full UUID partition must cover every selected source object exactly once.
  Missing, duplicated or stale UUIDs fail closed.
- All members keep individual original geometry; the solver moves whole
  logical family packing blocks and performs the usual exact contour checks.
- Groups with incompatible rotation/locking constraints are rejected.
- Numeric category/value must agree before merge; changed numeric groups must
  be reverified. Unchanged mappings remain confirmed.
- Changes invalidate the previous Apply until a new fully verified solution
  is calculated.
- Auto grouping can be restored using the reset action; user needs to
  recalculate afterwards.
- Embedded Illustrator item tags are not implemented in this PR.
