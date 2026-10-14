# RC2 — public release readiness

**Product engine:** v0.7.2, no layout algorithm changes. Sources, platform installers and user documents remain separate.

## Release gates

- [ ] GitHub Actions Python/JS tests on Windows and macOS.
- [ ] Native Windows PyInstaller build, SHA-256 verification and frozen-worker layout smoke test.
- [ ] Native macOS PyInstaller build, SHA-256 verification and frozen-worker layout smoke test.
- [ ] Clean Windows machine without Python: CEP export, optimize, preview, apply in Illustrator.
- [ ] Clean macOS machine: same roundtrip on supported Illustrator.
- [ ] Tampered package must fail installation; uninstall must retain workspace/presets.
- [ ] Confirm third-party licenses and brand asset rights.
- [ ] Publish and independently check SHA-256 of every GitHub Release artifact.
- [ ] Adobe unsigned CEP developer mode enabled only with informed consent.

Build automation alone does NOT verify an Illustrator workflow. Until native tests pass this is a release candidate, not a production-supported installer. Executables and CEP are unsigned.

Distribute separate source ZIP, Windows/macOS portable ZIP, optional Windows Setup.exe. Manual CLI/source instructions remain part of the repository.
