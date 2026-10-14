import hashlib
import json
from pathlib import Path
from kiki_layout.gui_jobs import calculate


def test_release_source_has_bilingual_docs_and_separate_installers():
    project=Path(__file__).resolve().parents[1]
    for doc in ('README.md','README_RU.md','README_EN.md','docs/ru/INSTALL.md','docs/en/INSTALL.md',
                'installers/windows/install.cmd','installers/windows/install.ps1','installers/macos/install.command',
                'packaging/worker_entry.py','packaging/build_portable.py'):
        assert (project/doc).is_file(),doc
    assert 'runtime' not in [p.name for p in project.iterdir()]  # source ZIP is NOT bundled executable


def test_portable_staging_has_manifest_and_no_private_exports(tmp_path):
    from packaging_import_helper import load_packaging_build
    build=load_packaging_build()
    worker=tmp_path/'fake-platform-worker.exe'
    worker.write_bytes(b'MZTEST ONLY: synthetic PE fixture')
    # The public builder intentionally refuses a package without license texts.
    # Supply synthetic texts only inside this temporary test directory.
    legal=tmp_path/'synthetic-licenses'
    legal.mkdir()
    license_files=('PYTHON_LICENSE.txt','GEOS_LGPL-2.1.txt',
                   'SHAPELY-license.txt','NUMPY-license.txt')
    for name in license_files:
        (legal/name).write_text('TEST FIXTURE - NOT FOR DISTRIBUTION\n',encoding='utf-8')
    (legal/'VERSIONS.json').write_text(json.dumps({
        'python':'test','shapely':'test','numpy':'test','geos':'test',
        'licenses':{
            'python':['PYTHON_LICENSE.txt'],
            'shapely':['SHAPELY-license.txt'],
            'numpy':['NUMPY-license.txt'],
            'geos':['GEOS_LGPL-2.1.txt'],
        },
    }),encoding='utf-8')
    internal=worker.parent/'_internal'
    internal.mkdir()
    (internal/'geos_c-test.dll').write_bytes(b'GEOS LIBRARY TEST FIXTURE')
    (internal/'python312.dll').write_bytes(b'PYTHON RUNTIME TEST FIXTURE')
    root=tmp_path/'portable'
    build.build(worker,root,'windows',licenses_dir=legal)
    assert (root/'third_party_licenses/VERSIONS.json').is_file()
    assert (root/'runtime/kiki-worker.exe').read_bytes()==worker.read_bytes()
    assert (root/'runtime/_internal/python312.dll').exists()
    assert (root/'runtime/_internal/geos_c-test.dll').exists()
    assert 'runtime/_internal/geos_c-test.dll' in json.loads((root/'GEOS_FILES.json').read_text())
    assert (root/'README_RU.md').exists() and (root/'README_EN.md').exists()
    assert (root/'installers/windows/install.cmd').exists()
    assert not list(root.rglob('input_copy.json'))
    manifest=json.loads((root/'SHA256SUMS.json').read_text())
    for rel,digest in manifest.items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest
