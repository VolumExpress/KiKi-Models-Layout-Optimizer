"""Safety contracts for the requested-gap recovery policy.

No private AI exports are committed. These synthetic cases verify both the
original P10 cause (multi-row family gap regression) and reduced-gap auditing.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box
from shapely.affinity import translate

from kiki_layout import engine
from kiki_layout.engine import PackingFailure
from kiki_layout.families import build_units
from kiki_layout.gap_policy import optimize_gap


def test_wrapped_family_rows_respect_gap_after_vertical_centring():
    sizes = [(3, 3), (5, 3), (7, 4), (9, 5), (11, 9), (13, 13), (15, 15)]
    shapes = {str(i): box(0, 0, w, h) for i, (w, h) in enumerate(sizes)}
    objs = [{'id': str(i)} for i in range(len(sizes))]
    unit = build_units(objs, shapes, {str(i): 'family' for i in range(len(sizes))},
                       gap=4.5, max_group_width=45)[0]
    placed = [translate(shapes[oid], *unit['offsets'][oid]) for oid in unit['ids']]
    for i, a in enumerate(placed):
        for b in placed[i+1:]:
            assert a.distance(b) >= 4.5 - 1e-5


def test_adaptive_search_finds_largest_verified_candidate():
    def solve(gap, discovery):
        if gap > 3.225:
            raise PackingFailure('Cannot fit family in synthetic case')
        return {'verified': gap}, None
    solution, actual, audit = optimize_gap(
        4.5, solve, PackingFailure, seconds=0, precision_mm=.02)
    assert solution['verified'] == actual
    assert 3.20 <= actual <= 3.225
    assert audit['requested_mm'] == 4.5
    assert audit['reduced'] is True
    assert audit['approximate'] is True
    assert any(not x['feasible'] for x in audit['checked'])
    assert any(x['feasible'] for x in audit['checked'])


def test_gap_policy_does_not_hide_geometry_or_validation_errors():
    def invalid_geometry(gap, discovery):
        raise AssertionError('Gap violation: internal programming bug')
    with pytest.raises(AssertionError, match='programming bug'):
        optimize_gap(4.5, invalid_geometry, PackingFailure)
    def invalid_input(gap, discovery):
        raise ValueError('Invalid source geometry')
    with pytest.raises(ValueError, match='Invalid source geometry'):
        optimize_gap(4.5, invalid_input, PackingFailure)


def _plate():
    objects = []
    for idx, (symbol, size) in enumerate(
            [('A', 3), ('A', 5.5), ('B', 3), ('B', 5.5), ('C', 3), ('C', 5.5)]):
        objects.append({'id': str(idx), 'name': f'Symbol{symbol}__{size}mm',
                        'geometry': {'type': 'path',
                                     'ring': [[0, 0], [size, 0], [size, size], [0, size]]}})
    return {'schema': 1, 'document_name': 'P10-synthetic.ai',
            'artboard': {'width_mm': 85, 'height_mm': 50},
            'objects': objects}


def test_engine_adaptive_clearance_is_recorded_and_is_actually_used(monkeypatch):
    real = engine._layout_once
    def limit_gap(data, **options):
        if options['gap'] > 3.2:
            raise PackingFailure('Cannot fit family at synthetic requested clearance')
        return real(data, **options)
    monkeypatch.setattr(engine, '_layout_once', limit_gap)
    result, shapes = engine.layout(_plate(), mode='uniform', families='named',
                                   family_layout='family_first', flow='rows',
                                   adaptive_gap=True, trials=2,
                                   gap=4.5, margin=2, rotations=(0,),
                                   seed=42)
    actual = result['settings']['gap_mm']
    audit = result['report']['gap_adjustment']
    assert 3.17 <= actual <= 3.2
    assert audit['reduced'] is True
    assert result['settings']['requested_gap_mm'] == 4.5
    assert audit['used_mm'] == pytest.approx(actual, abs=1e-4)
    assert result['report']['family_layout']['mode'] == 'family_first'
    assert len(result['items']) == 6
    assert result['report']['within_margins']
    assert result['report']['min_clearance_mm'] >= actual - 1e-5
    assert any('Requested gap' in warning for warning in result['report']['warnings'])
