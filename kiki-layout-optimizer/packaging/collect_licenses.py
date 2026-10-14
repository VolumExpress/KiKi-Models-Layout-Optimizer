"""Collect redistributable license texts for the EXACT release build environment.

Runs during CI after dependencies are installed. Failure is intentional if a
license cannot be collected; do not publish incomplete binary distributions.
"""
from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import shutil
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def _copy_dist_license(dist_name: str, output: Path, prefix: str) -> list[str]:
    dist = metadata.distribution(dist_name)
    collected = []
    for f in dist.files or ():
        path = str(f).replace('\\', '/')
        basename = Path(path).name
        if not ('.dist-info/' in path and ('license' in path.lower() or 'copying' in path.lower())):
            continue
        original = Path(dist.locate_file(f))
        if original.is_file():
            filename = f'{prefix}-{basename}'
            destination = output / filename
            destination.write_bytes(original.read_bytes())
            collected.append(filename)
    if not collected:
        raise RuntimeError(f'No license metadata found for {dist_name}; stop publication')
    return sorted(collected)


def _python_license() -> bytes:
    """Prefer an installed CPython license; otherwise fetch the exact source tag."""
    major, minor, micro = sys.version_info[:3]
    for directory in [Path(sys.base_prefix), Path(sys.executable).resolve().parent, Path(sys.executable).resolve().parent.parent]:
        for name in ('LICENSE', 'LICENSE.txt', 'LICENSE.rst'):
            candidate = directory / name
            if candidate.is_file():
                content = candidate.read_bytes()
                if b'PYTHON SOFTWARE FOUNDATION LICENSE' in content.upper() and len(content) > 2000:
                    return content
    version = f'v{major}.{minor}.{micro}'
    url = f'https://raw.githubusercontent.com/python/cpython/{version}/LICENSE'
    req = urllib.request.Request(url, headers={'User-Agent': 'KiKi-Layout-Optimizer-release-license-collector'})
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read(250_000)
    if b'PYTHON SOFTWARE FOUNDATION LICENSE' not in content.upper() or len(content) < 2000:
        raise RuntimeError(f'Unexpected CPython LICENSE from {url}')
    return content


def collect(output: Path, *, python_license: bytes | None = None) -> dict:
    import numpy
    import shapely

    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    geos = ROOT / 'licenses' / 'GEOS_LGPL-2.1.txt'
    if not geos.is_file() or len(geos.read_bytes()) < 15000:
        raise RuntimeError('GEOS LGPL-2.1 full license missing')
    shutil.copy2(geos, output / 'GEOS_LGPL-2.1.txt')
    shapely_files = _copy_dist_license('shapely', output, 'SHAPELY')
    numpy_files = _copy_dist_license('numpy', output, 'NUMPY')
    python_text = python_license if python_license is not None else _python_license()
    if b'PYTHON SOFTWARE FOUNDATION LICENSE' not in python_text.upper() or len(python_text) < 2000:
        raise RuntimeError('Invalid CPython LICENSE: full license stack expected')
    (output / 'PYTHON_LICENSE.txt').write_bytes(python_text)

    geos_version = shapely.geos_version_string
    versions = {
        'python': sys.version.split()[0],
        'shapely': shapely.__version__,
        'numpy': numpy.__version__,
        'geos': geos_version,
        'licenses': {
            'python': ['PYTHON_LICENSE.txt'],
            'shapely': shapely_files,
            'numpy': numpy_files,
            'geos': ['GEOS_LGPL-2.1.txt'],
        },
        'upstream': {
            'python': f'https://github.com/python/cpython/tree/v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
            'shapely': f'https://github.com/shapely/shapely/releases/tag/{shapely.__version__}',
            'numpy': f'https://github.com/numpy/numpy/releases/tag/v{numpy.__version__}',
            'geos': f'https://github.com/libgeos/geos/releases/tag/{geos_version}',
        },
        'warning': 'See THIRD_PARTY_NOTICES.md: GEOS LGPL obligations, corresponding source and relinking assessment are NOT validated by this inventory.',
    }
    (output / 'VERSIONS.json').write_text(json.dumps(versions, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return versions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'third_party_licenses')
    args = parser.parse_args()
    versions = collect(args.output)
    print('Third-party notices collected: ' + ', '.join(f'{k}={versions[k]}' for k in ('python','shapely','numpy','geos')))


if __name__ == '__main__':
    main()
