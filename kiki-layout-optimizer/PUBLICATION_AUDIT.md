# RC2 source import audit

The existing repository root README is preserved. Product sources are under kiki-layout-optimizer/. Root workflows run against that directory.

All three supplied archive/bundle SHA-256 values matched the supplied checksum list. Installer Source Kit files exactly matched the source ZIP. No AI files, real input exports, user workspace or production vector datasets were found in the source ZIP. P10-style names in tests identify synthetic fixtures. Private historical reports were withheld; the PDF was excluded because its contents were not reviewed. Local benchmark paths now require explicit CLI inputs.

The Git history bundle is retained locally and is NOT imported or published: historical contents have not been audited. Only the inspected source snapshot is proposed.

Local test execution was unavailable (terminal CET failure; runtime spawn EPERM). GitHub CI results must be checked. Native Illustrator, clean-machine install/uninstall, signing and third-party/branding rights remain release gates. MIT code license is supplied; it does not establish ownership of branding assets or license compliance of frozen dependencies.

Build jobs upload separate portable ZIP/checksum and Windows Setup/checksum artifacts only, with contents:read; no GitHub Release publication or tag trigger. No installer is production-approved by this audit. macOS builds target the runner architecture, not a universal binary.
