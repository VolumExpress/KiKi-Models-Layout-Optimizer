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
    root=tmp_path/'portable'
    build.build(worker,root,'windows')
    assert (root/'runtime/kiki-worker.exe').read_bytes()==worker.read_bytes()
    assert (root/'README_RU.md').exists() and (root/'README_EN.md').exists()
    assert (root/'installers/windows/install.cmd').exists()
    assert not list(root.rglob('input_copy.json'))
    manifest=json.loads((root/'SHA256SUMS.json').read_text())
    for rel,digest in manifest.items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest
