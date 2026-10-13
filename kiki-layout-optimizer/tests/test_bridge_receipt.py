"""The Illustrator automation result must be confirmed by the JSX, not COM alone."""
import json
from pathlib import Path
import pytest
from kiki_layout.illustrator_bridge import run_action, IllustratorAutomationError
from kiki_layout.gui import LABELS, HELP


class Completed:
    returncode = 0
    stderr = ''
    stdout = ''


def scripts(tmp_path):
    (tmp_path/'illustrator').mkdir()
    (tmp_path/'illustrator'/'export_selection.jsx').write_text('/* script */')
    (tmp_path/'illustrator'/'apply_layout.jsx').write_text('/* script */')


def test_export_receipt_checks_actual_json_exists(tmp_path):
    scripts(tmp_path)
    exported = tmp_path/'workspace'/'P10'/'input_copy.json'
    def simulate_illustrator(*_args, **_kwargs):
        active = tmp_path/'workspace'/'_bridge'/'request.json'
        req = json.loads(active.read_text())
        exported.parent.mkdir(parents=True)
        exported.write_text('{"schema": 1, "objects": []}',encoding='utf-8')
        receipt = active.parent/(req['nonce']+'.json')
        receipt.write_text(json.dumps({'status':'ok','nonce':req['nonce'],
                                       'action':'export','path':str(exported)}))
        return Completed()
    result = run_action('export',root=tmp_path,platform='win32',runner=simulate_illustrator,verify=True)
    assert result['path']==str(exported)
    assert not (tmp_path/'workspace'/'_bridge'/'request.json').exists()
    assert not list((tmp_path/'workspace'/'_bridge').glob('*.json'))


def test_error_receipt_does_not_report_success(tmp_path):
    scripts(tmp_path)
    def failed_script(*_args, **_kwargs):
        active=tmp_path/'workspace'/'_bridge'/'request.json'
        req=json.loads(active.read_text())
        (active.parent/(req['nonce']+'.json')).write_text(json.dumps({
            'status':'error','nonce':req['nonce'],'action':'export',
            'detail':'No selected artwork'}))
        return Completed()
    with pytest.raises(IllustratorAutomationError,match='No selected artwork'):
        run_action('export',root=tmp_path,platform='win32',runner=failed_script,verify=True)


def test_export_receipt_missing_file_is_error(tmp_path):
    scripts(tmp_path)
    def false_receipt(*_args,**_kwargs):
        active=tmp_path/'workspace'/'_bridge'/'request.json'
        req=json.loads(active.read_text())
        (active.parent/(req['nonce']+'.json')).write_text(json.dumps({
            'status':'ok','nonce':req['nonce'],'action':'export','path':str(tmp_path/'absent.json')}))
        return Completed()
    with pytest.raises(IllustratorAutomationError,match='JSON file is missing'):
        run_action('export',root=tmp_path,platform='win32',runner=false_receipt,verify=True)


def test_language_labels_are_complete_and_buttons_have_no_numbers():
    assert set(LABELS['ru'])==set(LABELS['en'])
    for lang in ('ru','en'):
        assert not LABELS[lang]['ai_export'][0].isdigit()
        assert not LABELS[lang]['ai_apply'][0].isdigit()
        assert LABELS[lang]['log']
        assert HELP[lang]['rotation']
