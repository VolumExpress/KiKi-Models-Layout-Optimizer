# GEOS LGPL-2.1 — binary redistribution checklist

**Status:** technical release checklist, not a legal opinion. Perform the applicable audit before public redistribution of binaries.

## Distribution structure

- PyInstaller `--onedir` produces `runtime/kiki-worker(.exe)` plus `runtime/_internal/`; no separate Python installation is needed.
- `GEOS_FILES.json` identifies the exact relative names and SHA-256 of GEOS shared libraries under `runtime/_internal/`.
- `third_party_licenses/` includes per-build versions and applicable license texts.
- The Windows Setup and macOS DMG wrap platform-specific portable payloads.

## GEOS replacement test

1. Extract a **copy** of the portable archive on the target OS, without touching an active KiKi installation.
2. Inspect `GEOS_FILES.json` and `third_party_licenses/VERSIONS.json`. Record shipped GEOS and Shapely versions, architecture and shared library names.
3. Build an **ABI-compatible** replacement GEOS of the same architecture. Preserve the original binaries and any loader-specific names/paths.
4. Substitute GEOS shared libraries in the copied `runtime/_internal/` (macOS may need additional consideration for Mach-O signing and loader rules).
5. Execute a **real synthetic layout calculation** with the changed bundled worker and confirm the replacement library was loaded; `--help` alone does not count.
6. Record test environment, hashes, versions and results. Installation-time SHA-256 verification may correctly reject modified input packages; verify installed-copy replacement separately.

## Legal release gate

- Review LGPL-2.1 §6 and confirm that the actual distribution/linking arrangement meets applicable obligations, including the ability to use a modified compatible GEOS where required.
- Arrange compliant access to the **corresponding GEOS source code** of the shipped version and any applicable modifications and instructions; an upstream URL alone is not automatically sufficient.
- Retain copyright notices and applicable license texts for every shipped third-party dependency.
- Perform the relevant checks for each OS; passing CI and exposing DLL/dylib files do not establish legal compliance.

Primary text: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
