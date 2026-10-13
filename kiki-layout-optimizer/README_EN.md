# KiKi Models Layout Optimizer v0.7.2 Beta

[Home](README.md) · [Русский](README_RU.md)

**Purpose:** A contour-aware Illustrator panel for arranging vector shapes on engraving or cutting stock. It is **not CAM software** and does not control laser machinery.

## New in v0.7.2 — Smart Family Layout

### New family-report review

Grouping controls *which objects belong together*; Family layout controls *where those recognized groups are positioned*. CEP provides clear inline help, and a compact family report with opt-in technical IDs.

## Features

- **Dense:** compact footprint; **Uniform:** more consistent neighbour spacing; **Ordered:** preserves the original selection sequence, not absolute coordinates.
- Minimum clearances, four independent edge margins, 0/90/180/270° rotations, per-object rotation limits and locked source positions.
- Family grouping by code, approximate normalized silhouette, or off. Automatic grouping is fallible: visually review the family audit.
- Multistart, seeded reproducibility, soft time budget, experimental LNS/NFP and **v0.7.1 optional/experimental objective-guided candidate construction (off by default)** (area, nearest spacing, centroid travel). No global optimality guarantee.
- Validated **Pareto preview-only** alternatives under `workspace/<document>/alternatives/`. Only the selected finished `result_test.json` may be applied back in Illustrator.
- Revision-safe export: export history and UUID/geometry-based reconciliation of constraints; stale results are invalidated.
- Cutting beta adds kerf-aware spacing of **separate** parts, coincident-edge inspection, and an experimental de-duplicated vector linework *draft* for already touching source polygons — **no kerf compensation, CAM, G-code, lead-ins or machine-safe cutting order**.

## Compatibility

- Windows + **Illustrator 30.6.0.109**: user-tested CEP, export, optimization and apply for previous versions v0.5.1–v0.7.1. **User confirmed the v0.7.2 UI/Docs RC1 full Illustrator workflow on Windows / 30.6.0.109; macOS remains untested on native hardware.**
- macOS integration/build scripts supplied, **native functionality unverified**. Test exact supported Illustrator versions before a production release.
- Current panel: CEP / Extensions (Legacy); migration to UXP will replace the adapter, not the Python geometry engine.

## End-user installation (no separate Python)

1. Download a **separate platform-built** `KiKi-v0.7.2-windows-portable.zip` or `KiKi-v0.7.2-macos-portable.zip`. A source archive with no `runtime` directory is *not* a standalone packaged distribution.
2. Extract and inspect the readable scripts, license and `SHA256SUMS.json` / `SHA256SUMS.txt`. The installer verifies package hashes before copying.
3. Run `installers/windows/install.cmd` on Windows or `installers/macos/install.command` on macOS. The installer verifies SHA-256 checksums and copies the bundled worker into a per-user application directory and preserves existing `workspace` and presets.
4. **Unsigned CEP Beta:** Adobe developer debug mode (CSXS.11/12) is **explicitly opt-in**. Enabling it reduces an application trust barrier. Do so only if you trust and have checked the extension. No signed production CEP installer exists yet.
5. Restart Illustrator and find **Window → Extensions (Legacy) → KiKi Layout Optimizer**. Troubleshooting: [installation guide](docs/en/INSTALL.md).

An optional Windows GUI `KiKi-v0.7.2-Windows-Setup.exe` is an **independent artifact** produced by Windows CI after a successful build; never included inside source ZIP and never assumed to exist before CI succeeds.

## Install from source / command line

Requires Python 3.10+, pip and Shapely 2.x. **No CMake, C++ compiler or Visual Studio Build Tools.**

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m kiki_layout.cep_install --enable-unsigned-dev
```

macOS terminal:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[test]'
./.venv/bin/python -m kiki_layout.cep_install --enable-unsigned-dev
```

Remove the explicit `--enable-unsigned-dev` flag if you do not consent to unsigned CEP debug mode. CLI example:

```bash
python -m kiki_layout.cli workspace/example/input_copy.json -o layout.json --mode uniform --gap 0.8 --families named --rotations 0 --trials 4 --seed 42 --svg preview.svg
```

See `python -m kiki_layout.cli --help` for all switches. CEP selection controls require a running Illustrator instance.

## In-panel help

Help is provided for quick start, technology, optimization mode, silhouette matching, rotations, clearances, family arrangement, object constraints, presets and objective priorities. Experimental methods remain flagged, while version-specific engineering terms are kept out of primary labels.

## Illustrator workflow

**Work on a copy of `.ai`**. Select the relevant vector objects → Export Selection → adjust technology, dimensions, groupings and rotations → Optimize → review metrics, SVG and preview-only Pareto alternatives → Apply in Illustrator. Select individual emblems in Illustrator to lock/limit rotation via CEP; re-export after editing source artwork. Applying a result changes object positions and may change allowed rotations.

## Safety and limitations

- Heuristics do not guarantee optimal packing, identical minimum spacing everywhere or correct visual identification of families.
- Centroid jump distance **is not actual laser travel time**.
- Cutting **does not perform production common-line merging of newly packed parts**, kerf-compensated output, CAM, G-code, kerf sequencing, tabs or inner-before-outer routing. The shared-line vector draft of original touching polygons is **not machine-ready and must not be cut directly**.
- Do not commit private vector designs (`.ai`, P10/P11 exports), user workspace, logs, secrets or customer artwork into this public repository.

## Output, tests, documentation

Per-document `workspace/<name>/input_copy.json`, `result_test.json`, `preview_test.svg`, `route_test.csv/svg`, `history/`, `constraints.json` and `alternatives/`. Benchmark reproducibly with exact exported contours, spacing, rotations, trial count, seed and engine version. `python -m pytest -q`; JS tests: `for f in tests/*.cjs; do node "$f"; done` (bash / Git Bash).

[Architecture](docs/architecture.md) · [Install and remove](docs/en/INSTALL.md) · [Cutting](docs/cutting-mode.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [MIT code license](LICENSE). Third-party dependencies have their own licenses; code licensing does not grant rights to Warhammer or other copyrighted images.


### RC2: release checks
[RC2 release checklist](docs/en/RELEASE_RC2.md) — native Windows/macOS tests, no-Python installation checks and license audit before public release.
