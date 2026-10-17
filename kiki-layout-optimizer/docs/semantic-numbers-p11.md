# P11: semantically ordered number families (experimental)

The existing `uniform`, `dense`, `ordered`, `compact` and `family_first` workflows remain unchanged unless the new **Semantic number order** checkbox is selected.

## Usage (Russian/English panel)

1. Export your **copy** of the P11 Illustrator plate normally.
2. Put a `semantic_order.json` file alongside `input_copy.json` in that plate's own `workspace/<plate>` folder.
3. Enable **Упорядоченные семейства / Ordered Families**, **Рядами / Rows**, **0°**, and choose **Uniform** or **Dense**.
4. Enable **Смысловой порядок чисел / Semantic number order**.
5. Calculate and inspect the preview and the semantic audit before applying.

The manifest is **private user data** and is not included in this public repository. Example with synthetic values:

```json
{
  "schema": 1,
  "document_name": "P11_synthetic.ai",
  "entries": {
    "sym:p11-sym-001": {"section": "roman", "value": 1, "status": "confirmed"},
    "sym:p11-sym-002": {"section": "roman", "value": 2, "status": "confirmed"},
    "uuid:illustrator-object-123": {"section": "carrier", "value": null, "status": "provisional"}
  }
}
```

`document_name` must exactly match the Illustrator export. Entry keys match symbol codes embedded in object names (size-independent), or explicit Illustrator UUIDs for technical names like `item-42`.

Valid `section`: `roman`, `gothic`, `carrier`, `other`.
`value`: integer 1–500 for roman/gothic; nullable for carriers/other. `status`: `confirmed` (visually verified) or `provisional` (must be checked).

## Safety

- Semantic order is **strict**: it never silently converts to Compact or MaxRects, because those methods may scramble numerical sequences.
- The ordinary geometric validation still checks real contour separation, margins, IDs and rotations.
- With adaptive gap enabled, the engine may try smaller gaps; any reduction is explicitly recorded and needs user confirmation.
- Invalid or conflicting numeric identities inside the same detected family stop the calculation.
- Unmapped families are retained, placed **after** mapped families, and reported. The UI requires explicit confirmation before applying a result with unresolved or provisional semantic labels.
- `status=provisional` does not mean the number is correct. Verify symbols, especially gothic lettering and numbers inside decorative carriers.
- Sorting by family value does **not** override Illustrator geometry correctness; visually check actual glyph reading order after calculation.
- Avoid uploading private P11 artwork or the user-specific mapping to the public repository.

## Known limitations

- Incomplete labels reduce semantic coverage.
- Strict family order is less space-efficient than unconstrained packing and may not fit at a requested large gap.
- The manifest currently travels with the **individual exported document**, not the general saved preset. General presets store the checkbox only.
- This is not OCR. The app does not infer glyph semantics from arbitrary paths.

Regression tests: `tests/test_semantic_order_p11_v074.py`.
