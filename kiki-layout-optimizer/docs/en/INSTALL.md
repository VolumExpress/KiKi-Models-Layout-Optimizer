# KiKi Models installation, upgrade and removal

## Release artifact separation

Source ZIP, Windows portable ZIP, macOS portable ZIP and optional Windows graphical `Setup.exe` are **separate** downloads. Verify provenance, operating system and `SHA256SUMS.json`. Source ZIP is not a prebuilt runtime.

### Windows without Python

1. Extract the native-built Windows portable archive.
2. Review and launch `installers/windows/install.cmd` (which runs readable `install.ps1`).
3. The unsigned Adobe CEP beta requires **explicit consent** to enable per-user `PlayerDebugMode` (CSXS.11/12), which lowers the trust barrier for unsigned panels.
4. Restart Illustrator. Application: `%LOCALAPPDATA%\KiKiModels\LayoutOptimizer`; CEP: `%APPDATA%\Adobe\CEP\extensions\com.kikimodels.layoutoptimizer`.
5. If absent, check Extensions (Legacy), installed Illustrator version, `config.js` and voluntary unsigned developer mode.

CLI-style install from the extracted portable package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\windows\install.ps1
# Only with informed consent:
powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\windows\install.ps1 -EnableUnsignedDev
```

### macOS without Python

Run `installers/macos/install.command` from a macOS-built portable package. Gatekeeper may require explicitly allowing a locally developed unsigned application. Installs under `~/Library/Application Support/KiKiModels/LayoutOptimizer`. macOS Illustrator CEP integration has not been natively tested.

## Upgrade and uninstall

Close Illustrator before upgrading. Run the new portable installer; it preserves `workspace` and `presets`, but **back them up** alongside `.ai` files. On uninstall close Illustrator and remove the CEP extension folder and app directory after backing up user data. Do not silently modify CSXS debug mode if other Adobe extensions use the same preference; remove those preferences manually only after checking.

## Troubleshooting

- CEP not visible: confirm Legacy Extensions menu, per-user install path, Illustrator version and explicitly opted-in unsigned developer mode.
- Missing runtime: downloaded source instead of native portable package; either use source+Python or download a runtime bundle.
- Stale object/geometry: re-export selection and inspect `export_audit.json` and `constraints.json`.
- Missing result: inspect workspace logs, never apply `best_so_far.json` or preview-only Pareto alternatives.
- Build from sources on each target OS; portable binaries are not cross-compiled in this repository.


## RC2 payload integrity and uninstall

Portable packages include `SHA256SUMS.txt` and `SHA256SUMS.json`. Installer scripts verify package hashes **before** installation. Hashes detect accidental/tampered files only relative to the obtained manifest; compare the release ZIP's SHA-256 against a trusted GitHub Release. No publisher-signing/notarization claim is made.

Windows: run `installers\windows\uninstall.cmd` (or `uninstall.ps1`); macOS: `installers/macos/uninstall.command`. User `workspace` and `presets` are kept by default. Adobe developer-mode preferences are left unchanged since other extensions may depend on them.

Windows/macOS builds still need packaged-worker smoke testing and native Illustrator roundtrip testing. Unsigned release candidates are not certified production builds.
