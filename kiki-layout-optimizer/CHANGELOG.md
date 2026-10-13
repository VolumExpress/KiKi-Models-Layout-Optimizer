## v0.7.2 RC2 — release engineering only (no changes to nesting algorithm)
- Deterministic platform payload SHA-256 manifest in JSON and text formats; installer verifies hashes before copying.
- Build-time smoke-test of the **frozen** Python worker on public synthetic geometry, on each OS.
- Separate auditable CLI installers and uninstall scripts that preserve `workspace` and `presets` by default.
- Optional Windows GUI installer checks installer failures and registers uninstaller in the user's apps list.
- Pre-publication RU/EN release-gate checklists and compatibility truthfulness.

## UI and documentation audit — pre-packaging update (2026-10-13)

# Changelog

## v0.7.2 Beta — Smart Family Layout


## v0.7.1 Beta — Python-first guided optimization and release packaging

- Optional objective-guided candidate construction for Free/Dense/Uniform, OFF by default because some profiles regress relative to v0.7.0; `Ordered`/rows/columns preserve their explicit ordering priorities.
- Pareto nondominated layout alternatives are stored as **preview-only** local JSON/SVG; only validated completed final output may be applied through CEP.
- Experimental unique shared-boundary linework SVG+JSON preview of **original adjacent cutting parts**, with strict overlap refusal; **not CAM, not kerf compensated, not applicable to packed parts**.
- CEP can select bundled executable worker or `.venv` source worker; platform release builder and optional Windows NSIS recipe added.
- Russian/English README, installation, safety notes, CI workflows and audit documentation.
- No mandatory C++ toolchain or new Python runtime dependency; previous placement/constraints remain the safe fallback.

## v0.7.0 Beta — three-objective selection

- Weighted area / nearest-gap regularity / proxy centroid travel, Pareto trial report.
- Inspection-only common-edge audit for cutting source selections.

## v0.6.4 — revision and family grouping fixes

- UUID/geometry-safe re-export, automatic family silhouette normalization and experimental Python LNS.

For earlier technical history see `docs/` and Git tags.
