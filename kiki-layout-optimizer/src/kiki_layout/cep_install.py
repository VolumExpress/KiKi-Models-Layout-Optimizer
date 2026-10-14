"""Install the optional UNSIGNED KiKi CEP beta, per-user, without admin rights.

Only the CEP UI/JSX adapter is copied; core Python optimizer stays at its
original location, and can later be reused with UXP.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXTENSION = 'com.kikimodels.layoutoptimizer'


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cep_user_folder(platform: str | None = None, home: Path | None = None, appdata: Path | None = None) -> Path:
    platform = platform or sys.platform
    home = home or Path.home()
    if platform == 'win32':
        appdata = appdata or Path(os.environ.get('APPDATA', home/'AppData'/'Roaming'))
        return appdata/'Adobe'/'CEP'/'extensions'
    if platform == 'darwin':
        return home/'Library'/'Application Support'/'Adobe'/'CEP'/'extensions'
    raise RuntimeError('CEP installer is supported only on Windows and macOS')


def install(root: Path, destination: Path) -> Path:
    origin = root/'cep'/EXTENSION
    if not (origin/'CSXS'/'manifest.xml').is_file():
        raise FileNotFoundError('CEP source package not found: '+str(origin))
    target = destination/EXTENSION
    destination.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        shutil.rmtree(target)
    shutil.copytree(origin, target)
    # No executable code interpolation: path JSON is a JS-safe quoted string.
    config='window.KIKI_PROJECT_ROOT = '+json.dumps(str(root.resolve()),ensure_ascii=True)+';\n'
    (target/'config.js').write_text(config, encoding='utf-8')
    return target


def enable_unsigned_dev(platform: str | None = None):
    """Requires explicit --enable-unsigned-dev. Not a production signed installer."""
    platform=platform or sys.platform
    if platform == 'win32':
        import winreg
        for n in (11,12):
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Adobe\CSXS.{n}') as key:
                winreg.SetValueEx(key, 'PlayerDebugMode', 0, winreg.REG_SZ, '1')
    elif platform == 'darwin':
        for n in (11,12):
            subprocess.run(['defaults','write',f'com.adobe.CSXS.{n}','PlayerDebugMode','-int','1'],check=True)


def main() -> int:
    ap=argparse.ArgumentParser(description='Install experimental unsigned Illustrator CEP panel (Windows/macOS)')
    ap.add_argument('--enable-unsigned-dev',action='store_true',help='Explicitly enable Adobe CSXS.11/12 PlayerDebugMode for unsigned local developer extension')
    args=ap.parse_args()
    root=source_root()
    target=install(root,cep_user_folder())
    print('KiKi Unified CEP BETA copied to:',target)
    print('Project root:',root)
    if args.enable_unsigned_dev:
        enable_unsigned_dev()
        print('Developer-only unsigned-extension mode enabled for CSXS.11 and CSXS.12 (current user).')
    else:
        print('Unsigned extension may not appear. See docs/cep-beta.md for manual developer mode.')
    print('Restart Illustrator and look under Window > Extensions (Legacy) > KiKi Layout Optimizer (Unified Beta).')
    print('If that menu is missing, continue using the working standalone GUI and manual JSX; compatibility is unverified.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
