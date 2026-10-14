"""Non-destructive CI check: use a separately compiled ABI-compatible GEOS.

Run from the KiKi project root after building a PyInstaller --onedir payload
and compiling the exact pinned GEOS source release with CMake. The published
ZIP/DMG/Setup are never changed. This is technical evidence, not legal advice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from smoke_runtime import smoke


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compiled_libs(prefix: Path) -> tuple[Path, Path]:
    """Return the actual C++ and C API libraries, avoiding symlink aliases."""
    ext = '.dll' if sys.platform == 'win32' else '.dylib'
    candidates = [p for p in prefix.rglob('*') if p.is_file() and p.name.lower().endswith(ext)]
    def find(capi: bool) -> Path:
        matched = [p for p in candidates if ('geos_c' in p.name.lower()) == capi
                   and 'geos' in p.name.lower()]
        if not matched:
            raise RuntimeError(f'Missing freshly compiled GEOS {"C" if capi else "C++"} shared library in {prefix}')
        if sys.platform == 'win32':
            exact = 'geos_c.dll' if capi else 'geos.dll'
        else:
            exact = 'libgeos_c.1.20.5.dylib' if capi else 'libgeos.3.14.1.dylib'
        preferred = [p for p in matched if p.name.lower() == exact.lower()]
        return (preferred or sorted(matched, key=lambda x: (x.is_symlink(), -len(x.name))))[0].resolve()
    return find(False), find(True)


def retarget_macos_c_api(path: Path, geos_file: str) -> None:
    """Resolve the rebuilt GEOS C++ dependency next to its rebuilt C API."""
    output = subprocess.check_output(['otool', '-L', str(path)], text=True)
    for line in output.splitlines()[1:]:
        dependency = line.strip().split(' (compatibility version', 1)[0].strip()
        name = Path(dependency).name
        if 'libgeos' in name.lower() and 'libgeos_c' not in name.lower():
            subprocess.run(['install_name_tool', '-change', dependency,
                            '@loader_path/' + geos_file, str(path)], check=True)
    # Ad hoc-sign only the newly compiled local test copies, never release files.
    subprocess.run(['codesign', '--force', '--sign', '-', str(path)], check=True)


def audit(payload: Path, built: Path, source_dir: Path, output: Path) -> dict:
    if sys.platform not in ('win32', 'darwin'):
        raise RuntimeError('This audit must run on a native Windows or macOS runner')
    payload, built = payload.resolve(), built.resolve()
    expected = json.loads((payload / 'third_party_licenses' / 'VERSIONS.json').read_text(encoding='utf-8'))
    if expected.get('geos') != '3.14.1':
        raise RuntimeError(f'Unexpected bundled GEOS version: {expected.get("geos")}')
    version = (source_dir / 'Version.txt').read_text(encoding='utf-8')
    for line in ('GEOS_VERSION_MAJOR=3', 'GEOS_VERSION_MINOR=14', 'GEOS_VERSION_PATCH=1'):
        if line not in version:
            raise RuntimeError(f'GEOS source version mismatch: missing {line}')
    inventory = json.loads((payload / 'GEOS_FILES.json').read_text(encoding='utf-8'))
    if not inventory:
        raise RuntimeError('Empty GEOS library inventory')
    original_cxx, original_c = compiled_libs(built)
    original_cxx_sha, original_c_sha = checksum(original_cxx), checksum(original_c)

    # Also verify that the *original release payload* passes geometry checks.
    smoke(payload)
    with tempfile.TemporaryDirectory(prefix='kiki-geos-replacement-') as temp:
        tmp = Path(temp)
        changed = tmp / 'modified-copy'
        shutil.copytree(payload, changed)
        replaced = {}
        c_libraries = []
        for rel, stored_hash in inventory.items():
            dest = changed / rel
            orig = payload / rel
            if not orig.is_file() or checksum(orig) != stored_hash:
                raise RuntimeError(f'Original GEOS checksum incorrect: {rel}')
            is_c = 'geos_c' in dest.name.lower()
            source = original_c if is_c else original_cxx
            shutil.copy2(source, dest)
            if sys.platform == 'win32' and is_c:
                # The rebuilt geos_c.dll has an import of geos.dll, while the
                # original Shapely wheel uses hashed filenames. Supply the
                # compiled dependency in the same directory as its C API DLL.
                shutil.copy2(original_cxx, dest.parent / 'geos.dll')
            if sys.platform == 'darwin':
                if is_c:
                    geos_name = next((Path(k).name for k in inventory
                                      if Path(k).parent == Path(rel).parent
                                      and 'geos_c' not in Path(k).name.lower()), '')
                    if not geos_name:
                        raise RuntimeError(f'Could not find GEOS sibling for {rel}')
                    retarget_macos_c_api(dest, geos_name)
                else:
                    subprocess.run(['codesign', '--force', '--sign', '-', str(dest)], check=True)
            new_hash = checksum(dest)
            if new_hash == stored_hash:
                raise RuntimeError(f'Replacement did not change the library: {rel}')
            replaced[rel] = {'original_sha256': stored_hash, 'replacement_sha256': new_hash}
            if is_c:
                c_libraries.append(rel)

        # Run the *real*, separately compiled libraries with the same worker.
        smoke(changed)
        if not c_libraries:
            raise RuntimeError('No C API library present: replacement not meaningful')

        # Fail-closed control: break every GEOS C API library in a second copy.
        # If the synthetic calculation still succeeds, an untouched GEOS is
        # being loaded from somewhere else, so the audit cannot pass.
        sabotaged = tmp / 'negative-control'
        shutil.copytree(changed, sabotaged)
        for rel in c_libraries:
            (sabotaged / rel).write_bytes(b'NOT_A_VALID_GEOS_SHARED_LIBRARY')
        failed_as_expected = False
        try:
            smoke(sabotaged)
        except (RuntimeError, OSError, ValueError, subprocess.SubprocessError):
            failed_as_expected = True
        if not failed_as_expected:
            raise RuntimeError('Negative control unexpectedly succeeded: GEOS loader is using another library')

        report = {
            'status': 'pass',
            'platform': platform.platform(),
            'architecture': platform.machine(),
            'geos_version': expected['geos'],
            'rebuilt_geos_cpp_sha256': original_cxx_sha,
            'rebuilt_geos_c_sha256': original_c_sha,
            'replacement_libraries': replaced,
            'real_layout_with_rebuilt_geos': True,
            'invalid_geos_negative_control_failed': True,
            'limits': ['Does not certify LGPL compliance',
                       'Does not establish that official tarball precisely reproduces bundled wheel build',
                       'Checks compatibility only on the recorded runner architecture'],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--payload', type=Path, required=True)
    p.add_argument('--built', type=Path, required=True)
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit(args.payload, args.built, args.source_dir, args.output), indent=2))


if __name__ == '__main__':
    main()
