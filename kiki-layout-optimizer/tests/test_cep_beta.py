"""CEP beta packaging contract, without claiming real Illustrator availability."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from kiki_layout.cep_install import EXTENSION, cep_user_folder, install, source_root
from kiki_layout.gui import HELP


def test_compact_family_help_contains_all_modes():
    for locale in ('ru','en'):
        title,body=HELP[locale]['family']
        assert title and all(x in body for x in ('off', 'named', 'auto'))
        assert len(body)<320


def test_cep_manifest_targets_illustrator_2026():
    root=source_root()
    base=root/'cep'/EXTENSION
    node=ET.parse(base/'CSXS'/'manifest.xml').getroot()
    host=node.find('./ExecutionEnvironment/HostList/Host')
    assert host.attrib['Name']=='ILST'
    assert host.attrib['Version']=='[30,31)'
    runtime=node.find('./ExecutionEnvironment/RequiredRuntimeList/RequiredRuntime')
    assert runtime.attrib['Name']=='CSXS'
    assert (base/'index.html').exists()
    assert (base/'host.jsx').exists()
    js=(base/'panel.js').read_text(encoding='utf-8')
    assert '__adobe_cep__.evalScript' in js and 'kikiCepAction' in js
    assert 'GetObject' not in js
    params=[x.text for x in node.findall('.//CEFCommandLine/Parameter')]
    assert '--enable-nodejs' in params
    assert '--mixed-context' in params
    assert 'kiki_layout.cep_worker' in js
    assert 'spawn(' in js
    assert 'launch_gui_' not in js


def test_cep_copy_is_user_local_and_sets_escaped_path(tmp_path):
    root=source_root()
    path=install(root, tmp_path/'extensions')
    assert path.name==EXTENSION
    config=(path/'config.js').read_text(encoding='utf-8')
    assert config.startswith('window.KIKI_PROJECT_ROOT = ')
    assert json.loads(config.split('=',1)[1].strip().rstrip(';'))==str(root.resolve())
    assert (path/'CSXS'/'manifest.xml').is_file()
    assert (path/'kiki-icon.png').is_file()
    assert not (path/'workspace').exists()


def test_win_mac_destinations(tmp_path):
    assert cep_user_folder('win32',tmp_path,tmp_path/'Roaming')==tmp_path/'Roaming'/'Adobe'/'CEP'/'extensions'
    assert cep_user_folder('darwin',tmp_path)==tmp_path/'Library'/'Application Support'/'Adobe'/'CEP'/'extensions'
