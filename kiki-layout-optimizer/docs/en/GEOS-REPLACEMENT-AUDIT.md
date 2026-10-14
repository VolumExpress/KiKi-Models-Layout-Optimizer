# GEOS replacement audit for v0.7.2 Beta

This is an **independent technical test**, not a legal compliance opinion.
It does not modify the published Windows Setup, Portable ZIP or macOS DMG.

## Method

1. Workflow `GEOS LGPL technical replacement audit` builds the frozen KiKi `--onedir` runtime on native Windows and macOS GitHub runners.
2. Downloads the **official** GEOS 3.14.1 source archive; checks its pinned SHA-256 `3c20919cda9a505db07b5216baa980bacdaa0702da715b43f176fb07eff7e716` and `Version.txt`.
3. Compiles fresh GEOS shared libraries with CMake on each platform. End users do **not** need CMake or a compiler.
4. Replaces GEOS only in temporary copies of the portable payload, including Shapely's hashed Windows DLL names and duplicate macOS dylib locations.
5. Runs a real synthetic layout with the rebuilt libraries and verifies their hashes differ from the shipped ones.
6. Runs a negative control by invalidating every GEOS C API shared library in a second copy; the layout must then fail. This helps detect accidental loading of an untouched GEOS copy.

When both platforms pass, download `KiKi-GEOS-replacement-audit-windows` and `...-macos` and archive the `report.json` files with the release verification record.

## Limitations

- Success demonstrates operation with a **fresh, ABI-compatible build** on tested architectures. It does not prove that arbitrary incompatible modifications work.
- An upstream source archive alone does not establish provenance or build equivalence of the libraries bundled by a Shapely wheel. Verify the exact wheel's GEOS source/build inputs, and arrange matching sources/patches where applicable.
- Check LGPL-2.1 obligations independently (notices, use of a modified compatible library, and corresponding source). A green CI run alone must not be represented as legal clearance.
- This does not constitute an Illustrator integration test on macOS.

After merging this workflow to `main`, rerun final platform builds and update the draft Release assets if the release tag and binary build commit must match exactly.
