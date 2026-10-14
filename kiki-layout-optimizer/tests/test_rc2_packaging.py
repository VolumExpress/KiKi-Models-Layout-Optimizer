"""Release and integrity checks; no real user Illustrator vectors involved."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'packaging'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_windows_payload_integrity(tmp_path):
    # Populate a mocked legal payload for isolated packaging tests.
    legal=tmp_path/'mock-licenses'
    legal.mkdir(parents=True, exist_ok=True)
    for fn in ('PYTHON_LICENSE.txt','GEOS_LGPL-2.1.txt','SHAPELY-license.txt','NUMPY-license.txt'):
        (legal/fn).write_text('SYNTHETIC TEST PLACEHOLDER\n',encoding='utf-8')
    (legal/'VERSIONS.json').write_text(json.dumps({
        'python':'3.12-test','shapely':'2-test','numpy':'2-test','geos':'3-test',
        'licenses':{'python':['PYTHON_LICENSE.txt'], 'shapely':['SHAPELY-license.txt'],
                    'numpy':['NUMPY-license.txt'], 'geos':['GEOS_LGPL-2.1.txt']}
    }),encoding='utf-8')
    worker=tmp_path/'worker.exe'
    worker.write_bytes(b'MZ-SYNTHETIC-TEST-ONLY')
    output=tmp_path/'package'
    load('build_portable').build(worker,output,'windows',licenses_dir=legal)
    count,errors=load('verify_payload').verify(output)
    assert count>20 and not errors
    assert (output/'SHA256SUMS.txt').read_text().count('\n')==count
    (output/'runtime/kiki-worker.exe').write_bytes(b'MZCORRUPT')
    _,errors=load('verify_payload').verify(output)
    assert any('Checksum mismatch' in e for e in errors)
    (output/'runtime/kiki-worker.exe').write_bytes(b'MZ-SYNTHETIC-TEST-ONLY')
    (output/'third_party_licenses/GEOS_LGPL-2.1.txt').write_text('CORRUPTED',encoding='utf-8')
    _,errors=load('verify_payload').verify(output)
    assert any('Checksum mismatch' in e for e in errors)


def test_reject_wrong_platform_worker(tmp_path):
    worker=tmp_path/'worker'
    worker.write_bytes(b'ELF-not-a-mac-executable')
    import pytest
    with pytest.raises(ValueError,match='Mach-O'):
        load('build_portable').build(worker,tmp_path/'portable','macos')


def test_manifest_rejects_traversal(tmp_path):
    output=tmp_path/'fake'
    output.mkdir()
    (output/'SHA256SUMS.json').write_text(json.dumps({'../escape':'0'*64}))
    _,issues=load('verify_payload').verify(output)
    assert any('Unsafe' in issue for issue in issues)


def test_installer_sources_are_separate_and_preserve_user_data():
    for relative in ('installers/windows/install.ps1','installers/windows/uninstall.ps1',
                     'installers/macos/install.command','installers/macos/uninstall.command'):
        content=(ROOT/relative).read_text(encoding='utf8')
        assert 'KiKiModels' in content or 'workspace' in content or 'SHA256SUMS' in content
    assert (ROOT/'packaging/smoke_runtime.py').is_file()
