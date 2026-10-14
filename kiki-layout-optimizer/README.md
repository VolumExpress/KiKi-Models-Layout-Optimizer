# KiKi Models Layout Optimizer · v0.7.2 Smart Family Beta

[Русский](README_RU.md) · [English](README_EN.md)

**Open-source contour-aware 2D layout helper for Adobe Illustrator**, with engraving and experimental cutting profiles. An HTML/JS CEP panel controls a Python engine (Shapely/GEOS); users can inspect every calculation and preserve their `.ai` source files.

![KiKi Models](assets/kiki-logo.png)

> **Production notice:** This is a beta layout tool, not CAM software. It does not generate validated laser toolpaths, common-line compensated cuts, G-code or machine-ready files. Always verify original contours, object identity, margins and tool paths in Illustrator/CAM before manufacture.

**New in v0.7.2:** optional **Ordered families** (whole size-series displayed consecutively) and opt-in **outline-weight-insensitive matching** for thin vector frames. Legacy compact layout remains the default. See [v0.7.2 details](docs/v0.7.2-smart-family-layout.md). **Pre-release UI/documentation audit:** [RU](docs/ru/FAMILY-LAYOUT-QA.md) / [EN](docs/en/FAMILY-LAYOUT-QA.md).

**Quick start:** choose the Windows/macOS transparent portable package from the GitHub Actions/Release artifacts, run `installers/windows/install.cmd` or `installers/macos/install.command`, restart Illustrator, then use **Window → Extensions (Legacy) → KiKi Layout Optimizer**. Unsigned CEP beta requires *explicit opt-in* developer mode and may not work on every Illustrator version. Full manual installation and command-line instructions are in the language-specific READMEs.

**What is distributed separately:**

- Source code archive / Git checkout — readable Python, JavaScript, JSX, scripts, tests and build recipes; no binaries required to audit it.
- Platform-specific portable package — prebuilt Python worker plus CEP files, an auditable command/script installer and SHA-256 file list; no end-user Python or C++ tools.
- Windows graphical `Setup.exe` — optional **separate** artifact built on Windows CI, never mixed with source archives.

[Features, installation, limitations (RU)](README_RU.md) · [Features, installation, limitations (EN)](README_EN.md) · [Security](SECURITY.md) · [RC2 release checklist RU](docs/ru/RELEASE_RC2.md) · [Release checklist EN](docs/en/RELEASE_RC2.md) · [Architecture](docs/architecture.md)