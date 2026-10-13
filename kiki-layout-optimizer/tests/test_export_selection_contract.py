"""Regression tests for Illustrator skipped-empty-group selection index contract."""
from kiki_layout.engine import layout


def test_sparse_original_selection_indices_roundtrip():
    data = {
        'schema': 1,
        'document_name': 'P10_TEST.ai',
        'source_selection_count': 4,
        'artboard': {'width_mm': 145, 'height_mm': 95},
        'skipped': [{'selection_index': 1, 'name': 'empty A', 'reason': 'empty group'},
                    {'selection_index': 2, 'name': 'empty B', 'reason': 'empty group'}],
        'objects': [
            {'id': '0', 'name': 'emblem 1', 'geometry': {'type': 'path',
                'ring': [[0, 0], [4, 0], [4, 4], [0, 4]]}},
            {'id': '3', 'name': 'emblem 2', 'geometry': {'type': 'path',
                'ring': [[0, 0], [3, 0], [3, 3], [0, 3]]}}
        ],
    }
    result, _ = layout(data, gap=.8)
    assert result['source_selection_count'] == 4
    assert {it['id'] for it in result['items']} == {'0', '3'}
    assert result['report']['within_margins']
