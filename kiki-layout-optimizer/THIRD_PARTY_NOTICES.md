# KiKi Models — third-party notices / Уведомления о сторонних компонентах

The KiKi Models source code is licensed under the separate project [`LICENSE`](LICENSE) (MIT). The KiKi Models logo and trademarks are owned by the KiKi Models project and **are not covered by the MIT code license**. No rights to third-party characters, brands or other artwork are granted by this package.

Исходный код KiKi Models распространяется под лицензией MIT (см. [`LICENSE`](LICENSE)). Логотип и обозначение KiKi Models принадлежат правообладателю проекта и **не входят в лицензию MIT на код**. Права на сторонние изображения, персонажей и товарные знаки не предоставляются.

## Binary release license contents / Лицензии бинарной сборки

Each Windows/macOS binary payload MUST include:

- `third_party_licenses/VERSIONS.json`: exact versions of **Python, Shapely, NumPy, GEOS** loaded in the native build environment and a record of upstream source locations.
- `third_party_licenses/PYTHON_LICENSE.txt`: complete CPython license stack (including PSF License) corresponding to the Python version bundled in the worker.
- `third_party_licenses/SHAPELY-*`: Shapely wheel's license notices, copied directly from the installed distribution metadata (BSD-3-Clause).
- `third_party_licenses/NUMPY-*`: NumPy wheel's actual license notices, including its third-party license notices where supplied in the wheel.
- `third_party_licenses/GEOS_LGPL-2.1.txt`: complete GNU LGPL 2.1 text, applicable to GEOS as used by Shapely.

These files are included in the checksum manifest and preserved in the installed application folder. CI fails if the collector cannot obtain a license. The macOS DMG contains the same checked portable payload, plus a Finder launcher.

Каждый готовый дистрибутив должен содержать точные версии компонентов, полные тексты лицензий и уведомлений. Их отсутствие блокирует сборку. DMG включает те же документы, что и macOS Portable.

## GEOS / LGPL-2.1 — additional release obligations

GEOS is a **separate LGPL-licensed library**. The fact that KiKi's own code is MIT-licensed, or that the GEOS license text has been included, **does not by itself discharge LGPL redistribution obligations**. Before publishing binary executables, the distributor must review the actual GEOS linking/bundling model used by **PyInstaller onefile**, verify its ability to replace or relink the bundled LGPL library where required, provide or arrange compliant access to the **corresponding GEOS source code** (including applicable modifications/build scripts), and meet any other obligations of the license. `VERSIONS.json` records the build's exact GEOS version and a corresponding upstream source location; an upstream link alone is not asserted to satisfy all applicable requirements. See GNU LGPL-2.1 sections 4 and 6.

GEOS распространяется по LGPL. Наличие текста LGPL и списка версий **само по себе не завершает проверку правомерности распространения**. Перед публикацией готового бинарника следует проверить модель динамической загрузки/замены GEOS внутри `PyInstaller --onefile`, обеспечить выполнение условий о соответствующих исходниках/возможности модификации и перелинковки в применимой форме, а также остальных условий LGPL. В `VERSIONS.json` фиксируется версия и ссылка на исходники; эта ссылка не считается универсальным подтверждением соответствия LGPL.

**Binary release gate / Условие публичного выпуска:** the GEOS LGPL compliance review must be completed independently of passing CI. Until then, built artifacts are technical release candidates, not legal clearance to distribute. / До отдельной проверки условий LGPL бинарники считаются техническими кандидатами на выпуск.

## GEOS onedir distribution / Распространение GEOS с onedir

The binary builder uses PyInstaller `--onedir` rather than `--onefile`.
GEOS shared libraries are separately visible under `runtime/_internal/`, and
`GEOS_FILES.json` lists their exact relative paths and SHA-256 digests. The
portable archive checksums cover them, as do the Windows Setup and macOS DMG
(both are built around the same portable payload).

Сборка размещает динамические библиотеки GEOS отдельными файлами в
`runtime/_internal/`; имена и контрольные суммы записаны в `GEOS_FILES.json`.
Пользователю не нужен установленный Python. Заменить библиотеку для
эксперимента можно в копии установленного приложения, соблюдая совместимость
ABI. Такая возможность **должна быть реально проверена на Windows/macOS**.

Technical replacement procedure: [RU](docs/ru/GEOS-DISTRIBUTION.md) / [EN](docs/en/GEOS-DISTRIBUTION.md).

**Release gate:** the physical presence of replaceable shared libraries alone
is NOT legal confirmation of compliance with LGPL-2.1 §6. Review the
application's actual loader behavior with a modified ABI-compatible GEOS,
applicable source-code distribution obligations, and all notices before
publishing binaries. See the upstream license at
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html .

## Build-only tooling / Инструменты сборки

- **PyInstaller**: GPL-2.0-or-later with the project's bootloader exception, permitting distribution of bundled applications under the application's license, subject to third-party dependency obligations. The PyInstaller development tool itself is not distributed with the KiKi source archive as part of the executable distribution. See https://pyinstaller.org/en/stable/license.html .
- **NSIS**: Windows Setup is produced with NSIS. NSIS source/plug-ins generally use the zlib/libpng license; its compression modules may have additional licenses depending on what the installer build actually includes. Check https://nsis.sourceforge.io/License and the NSIS source tree for the exact modules in the released installer.
- **GitHub Actions toolchains**: CPython and npm/Node in CI are tools. The compiled packages must include notices applicable to what is **actually bundled**, not every CI tool.

## Sources / Официальные источники

- Shapely: https://github.com/shapely/shapely/blob/main/LICENSE.txt
- GEOS: https://github.com/libgeos/geos/blob/main/COPYING
- Python: https://docs.python.org/3.12/license.html (exact source tag stored in `VERSIONS.json`)
- NumPy: https://numpy.org/doc/stable/license.html (actual installed-wheel license shipped in this package)
- PyInstaller: https://pyinstaller.org/en/stable/license.html
- NSIS: https://github.com/NSIS-Dev/nsis/blob/master/Docs/src/license.but

**Neither this notice nor CI is legal advice. / Данный файл и CI не заменяют юридическую проверку.**
