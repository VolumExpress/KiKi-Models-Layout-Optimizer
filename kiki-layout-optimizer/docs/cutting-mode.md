# Cutting profile — status and production safety (v0.4.1)

## Implemented

- `operation=engrave` retains previous geometry and all prior settings.
- `operation=cut` sets nominal contour clearance to **minimum material web + kerf**.
  E.g. `web=0.5 mm, kerf=0.15 mm` means target CAD contour clearance >=0.65 mm.
- Rotation, family grouping, four-sided margins and collision audit continue to work.
- JSON includes `operation`, `kerf_mm`, `requested_web_mm`, and a calculated
  `min_material_web_mm` for the heuristic contours.
- No destructive conversion of the original Illustrator geometry.

## NOT implemented — do not send geometry directly to a cutter

1. **Common-line cutting / shared-edge merging.** Adjacent parts can share a cut
   only when the tool-centerline is genuinely shared. Do not use `gap=0` as a shortcut:
   it may create kerf-dependent dimensional errors and cut pieces incorrectly.
2. **Toolpath offset** from part boundaries by +/- kerf/2 and hole-aware topology.
3. **Inner-before-outer** contours, sequencing, microtabs/bridges, lead-in/lead-out,
   pierce points, cut direction, cut ordering and thermal effects.
4. **Export to a cutting controller** (DXF/G-code etc.) and machine-specific validation.
5. Robust validation of clipped paths, live effects and nested open strokes in cutting.

## Engineering roadmap

- v0.5: per-object cut/engrave tags, lock position/orientation and refuse open cutting paths;
  cut-specific QA (minimum feature, part dimensions, hole nesting, edge tolerance).
- v0.6: benchmark NFP + local search vs current constructive heuristic, contour
  simplification at user-chosen tolerance and automatic nesting into holes.
- v0.7+: shared-line candidate detection -> common segment geometry -> union-of-segments
  toolpaths -> CAM export only after geometric and physical acceptance; cut order.

## Why separate cutting and engraving

Engraving paths may be filled/raster hatched; cutting follows tool-centerline offsets
around full components. The SVG preview in v0.4.1 is **not a manufacturing toolpath**.

References: https://github.com/deepnest-next/deepnest (common-line cutting and NFP approach)
