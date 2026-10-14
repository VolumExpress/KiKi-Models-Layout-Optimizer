"""Verification gates for distributed license texts."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'packaging'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_missing_inventory_fails_verification(tmp_path):
    root=tmp_path/'portable'
    root.mkdir()
    (root/'SHA256SUMS.json').write_text('{}',encoding='utf-8')
    _, errors=_load('verify_payload').verify(root)
    assert any('third-party' in e for e in errors)


def test_license_source_and_copy_paths_exist():
    assert (ROOT/'licenses/GEOS_LGPL-2.1.txt').stat().st_size > 15_000
    assert (ROOT/'packaging/collect_licenses.py').is_file()
    assert (ROOT/'THIRD_PARTY_NOTICES.md').is_file()
    for name in ('installers/windows/install.ps1','installers/windows/uninstall.ps1',
                 'installers/macos/install.command','installers/macos/uninstall.command'):
        content=(ROOT/name).read_text(encoding='utf-8')
        assert 'third_party_licenses' in content
        assert 'THIRD_PARTY_NOTICES.md' in content


def test_license_collector_versions_and_texts(tmp_path):
    collector=_load('collect_licenses')
    # Synthetic Python-license fixture is ONLY for this test; never published.
    fixture=b'PYTHON SOFTWARE FOUNDATION LICENSE' + (b' test-only' * 300)
    versions=collector.collect(tmp_path/'notices',python_license=fixture)
    assert versions['python']
    assert versions['geos']
    assert versions['shapely']
    assert versions['numpy']
    for files in versions['licenses'].values():
        assert files
        for name in files:
            assert (tmp_path/'notices'/name).is_file()
    assert json.loads((tmp_path/'notices/VERSIONS.json').read_text(encoding='utf-8'))['geos']==versions['geos']
