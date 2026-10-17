"""Regression tests for rigid-family rectangle rescue after shelf placement fails."""
import pytest
from shapely.geometry import box
from kiki_layout import engine
from kiki_layout.family_pack import pack_family_units
from kiki_layout.engine import collision_free, contained


def blocks():
    dimensions = [(48, 14, 'solid'), (42, 13, 'solid'),
                  (27, 13, 'solid'), (61, 12, 'mixed'),
                  (36, 18, 'mixed'), (26, 10, 'outline'),
                  (18, 7, 'outline')]
    return [{'family': str(i), 'ids': [str(i)],
             'geometry': box(0, 0, w, h), 'visual_style': style}
            for i, (w, h, style) in enumerate(dimensions)]


def test_rigid_rectangles_preserve_objects_clearances_and_are_deterministic():
    units = blocks()
    args = (units, 145, 95, (3, 3, 3, 3), 4.5)
    result = pack_family_units(*args, seed=42)
    assert result is not None and len(result) == len(units)
    again = pack_family_units(*args, seed=42)
    assert [shape.bounds for shape, *_ in result] == [shape.bounds for shape, *_ in again]
    taken = []
    for original, (shape, dx, dy, rotation) in zip(units, result):
        assert rotation == 0
        assert shape.area == pytest.approx(original['geometry'].area)
        assert contained(shape, 145, 95, (3, 3, 3, 3))
        assert collision_free(shape, taken, 4.5)
        taken.append(shape)


def test_rigid_rectangles_reject_impossible_board():
    assert pack_family_units(blocks(), 30, 20, (3, 3, 3, 3), 4.5) is None


def source():
    objects = []
    for index, (label, s) in enumerate(
        [('A', 3), ('A', 5.5), ('B', 3), ('B', 5.5),
         ('C', 3), ('C', 5.5)]
    ):
        objects.append({'id': str(index), 'name': f'Symbol{label}__{s}mm',
                        'geometry': {'type': 'path', 'ring':
                            [[0, 0], [s, 0], [s, s], [0, s]]}})
    return {'schema': 1, 'document_name': 'synthetic-family.ai',
            'artboard': {'width_mm': 65, 'height_mm': 45}, 'objects': objects}


def test_rescue_precedes_compact_fallback(monkeypatch):
    real = engine._layout_once
    called = []

    def force_shelf_failure(data, **options):
        mode = options.get('family_layout')
        method = options.get('family_packing_strategy', 'shelf')
        called.append((mode, method))
        if mode == 'family_first' and method == 'shelf':
            raise ValueError("Cannot fit family synthetic")
        return real(data, **options)

    monkeypatch.setattr(engine, '_layout_once', force_shelf_failure)
    result, _ = engine.layout(source(), mode='uniform', families='named',
                              family_layout='family_first', flow='rows',
                              gap=1, margin=2, trials=1)
    assert called[:2] == [('family_first', 'shelf'), ('family_first', 'maxrects')]
    assert result['report']['family_layout']['mode'] == 'family_first'
    assert result['report']['family_layout']['packing_strategy'] == 'maxrects'
    assert 'shelf_failure_reason' in result['report']['family_layout']
    assert result['report']['within_margins']
    assert len(result['items']) == 6
    assert result['report']['min_clearance_mm'] >= 1 - 1e-5


def test_rescue_does_not_violate_rotation_constraints(monkeypatch):
    real = engine._layout_once

    def force_shelf_failure(data, **options):
        if options.get('family_layout') == 'family_first' and options.get('family_packing_strategy') != 'maxrects':
            raise ValueError("Cannot fit family synthetic")
        return real(data, **options)

    monkeypatch.setattr(engine, '_layout_once', force_shelf_failure)
    result, _ = engine.layout(source(), mode='uniform', families='named',
                              family_layout='family_first', flow='rows',
                              rotations=(90,), gap=1, margin=2, trials=1)
    assert result['report']['family_layout']['mode'] == 'compact'
    assert result['report']['family_layout']['requested'] == 'family_first'
    assert result['report']['within_margins']
