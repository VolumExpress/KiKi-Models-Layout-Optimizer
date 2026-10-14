"""Create transparent no-Python-user payload from a platform-built worker.

Run from the source repository, after the PyInstaller build ON THE TARGET OS:
  python packaging/build_portable.py --worker dist/kiki-worker.exe --os windows
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_DIRS=('cep','illustrator','assets','installers')
PUBLIC_FILES=('LICENSE','README.md','README_RU.md','README_EN.md','CHANGELOG.md','THIRD_PARTY_NOTICES.md')
DOCS=('docs',)


def build(worker:Path, output:Path, os_name:str, *, licenses_dir:Path | None = None):
    worker=worker.resolve();output=output.resolve()
    if not worker.is_file(): raise FileNotFoundError(worker)
    # Do not accidentally distribute a Linux binary labelled as Windows/macOS.
    with worker.open('rb') as binary_file:
        magic = binary_file.read(4)
    if os_name == 'windows' and not magic.startswith(b'MZ'):
        raise ValueError('Windows worker must be a PE executable (MZ header)')
    if os_name == 'macos' and magic not in (bytes.fromhex('cffaedfe'),bytes.fromhex('feedfacf'),bytes.fromhex('cafebabe'),bytes.fromhex('bebafeca')):
        raise ValueError('macOS worker must be a Mach-O executable')
    if os_name not in ('windows','macos'):raise ValueError(os_name)
    if output == ROOT or (ROOT in output.parents and ROOT/'dist' not in output.parents):
        raise ValueError('Refusing to delete a source directory; output must be inside dist/ or outside the repo')
    if output in worker.parents:
        raise ValueError('Worker must not be located inside output, which is overwritten')
    legal_dir = (licenses_dir or ROOT / 'dist' / 'third_party_licenses').resolve()
    required = ('VERSIONS.json', 'PYTHON_LICENSE.txt', 'GEOS_LGPL-2.1.txt')
    if not legal_dir.is_dir() or any(not (legal_dir / file).is_file() for file in required):
        raise RuntimeError('Missing third-party licenses: run python packaging/collect_licenses.py before packaging')
    import json as _json
    versions = _json.loads((legal_dir / 'VERSIONS.json').read_text(encoding='utf-8'))
    for files in versions.get('licenses', {}).values():
        if not files or any(not (legal_dir / f).is_file() for f in files):
            raise RuntimeError('Incomplete third-party license inventory')
    if output.exists():shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(legal_dir, output / 'third_party_licenses')
    for d in PUBLIC_DIRS:
        shutil.copytree(ROOT/d,output/d,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
    for d in DOCS:
        src=ROOT/d
        if src.is_file(): (output/d).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,output/d)
        elif src.is_dir():shutil.copytree(src,output/d)
    for f in PUBLIC_FILES:
        if (ROOT/f).is_file():shutil.copy2(ROOT/f,output/f)
    (output/'runtime').mkdir()
    ext='.exe' if os_name=='windows' else ''
    binary=output/'runtime'/('kiki-worker'+ext)
    shutil.copy2(worker,binary);binary.chmod(0o755)
    (output/'workspace').mkdir()
    (output/'presets').mkdir()
    (output/'VERSION').write_text('0.7.2\n',encoding='utf8')
    manifest={}
    for file in sorted(output.rglob('*')):
        if file.is_file() and file.name not in ('SHA256SUMS.json','SHA256SUMS.txt'):
            manifest[file.relative_to(output).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    (output/'SHA256SUMS.json').write_text(json.dumps(manifest,sort_keys=True,indent=2),encoding='utf8')
    (output/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in sorted(manifest.items())),encoding='utf8')
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--worker',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=Path('dist/portable'))
    ap.add_argument('--os',choices=['windows','macos'],required=True)
    a=ap.parse_args();print(build(a.worker,a.output,a.os))
if __name__=='__main__':main()
