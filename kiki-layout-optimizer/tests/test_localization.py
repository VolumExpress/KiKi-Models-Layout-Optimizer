"""Localization should only affect messages, not geometry or schema."""
from __future__ import annotations
import json
from kiki_layout.cli import main
from kiki_layout.i18n import TEXTS, tr, local_warning


def test_all_messages_exist_in_both_languages():
    assert set(TEXTS['ru']) == set(TEXTS['en'])
    for lang in ('ru', 'en'):
        assert tr(lang, 'objects')
        assert tr(lang, 'saved', path='example.json')


def test_cli_two_languages_keep_same_geometry(tmp_path, capsys):
    source = {
        'schema': 1,
        'document_name': 'TEST.ai',
        'source_selection_count': 2,
        'artboard': {'width_mm': 30, 'height_mm': 20},
        'objects': [
            {'id': '0', 'name': 'One', 'geometry': {'type': 'path',
             'ring': [[0, 0], [4, 0], [4, 4], [0, 4]]}},
            {'id': '1', 'name': 'Two', 'geometry': {'type': 'path',
             'ring': [[0, 0], [2, 0], [2, 2], [0, 2]]}},
        ],
    }
    inp = tmp_path / 'input.json'
    inp.write_text(json.dumps(source), encoding='utf-8')
    results = []
    for lang in ('ru', 'en'):
        out = tmp_path / f'layout-{lang}.json'
        main([str(inp), '-o', str(out), '--mode', 'ordered', '--gap', '0.8',
              '--margin', '2', '--lang', lang, '--rotations', '0'])
        display = capsys.readouterr().out
        assert ('Объектов: 2' if lang == 'ru' else 'Objects: 2') in display
        results.append(json.loads(out.read_text(encoding='utf-8')))
    assert results[0] == results[1]


def test_translate_known_warnings():
    s = 'Laser jumps are CENTROID-PROXY estimates, not controller toolpaths or time savings.'
    assert 'центрами' in local_warning('ru', s)
    assert 'toolpaths' in local_warning('en', s) or 'toolpaths' in local_warning('en', s).lower()
