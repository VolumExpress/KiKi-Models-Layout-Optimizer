"""P01 regression: duplicate-point sampling artefacts are truly zero area.

Original Illustrator curves, valid micro-Bezier lenses and malformed nonempty
contours are never silently discarded.
"""
import copy

import pytest
from shapely.geometry import Polygon

from kiki_layout.geometry import (
    as_polygon, duplicate_point_ring_audit, from_tree, get_shapes,
)


def source():
    outside = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    repeated = [[-0.00968396481422, -1.61722725684494]] * 3
    repeated_2 = [[-0.01399406332835, -2.3370159934075]] * 3
    lens = [[0.0, 0.0], [0.0002, 0.0], [0.0, 0.0001]]
    return {
        "objects": [
            {"id": "42", "geometry": {"type": "group", "children": [{
                "type": "compound", "rings": [repeated, outside]}]}},
            {"id": "43", "geometry": {"type": "compound", "rings": [repeated_2, outside]}},
            {"id": "44", "geometry": {"type": "compound", "rings": [lens, outside]}},
        ]
    }


def test_exact_two_p01_empty_rings_are_audited_not_exported_as_ink():
    data = source()
    audit = duplicate_point_ring_audit(data)
    assert len(audit) == 2
    assert [x["object_id"] for x in audit] == ["42", "43"]
    shapes = get_shapes(data)
    assert set(shapes) == {"42", "43", "44"}
    assert shapes["42"].area == pytest.approx(4.0)
    assert shapes["43"].area == pytest.approx(4.0)
    assert shapes["44"].area == pytest.approx(4.0 - 1e-8)


def test_single_bad_ring_cannot_hide_a_missing_emblem():
    data = source()
    data["objects"][0]["geometry"] = {
        "type": "compound", "rings": [[[0, 0]] * 3]}
    with pytest.raises(ValueError, match="Empty geometry for object 42"):
        get_shapes(data)


def test_single_path_outside_compound_remains_strict():
    with pytest.raises(ValueError, match="Empty or degenerate"):
        from_tree({"type": "path", "ring": [[0, 0]] * 3})


def test_collinear_nonidentical_ring_is_not_silently_dropped():
    with pytest.raises(ValueError, match="Empty or degenerate"):
        from_tree({"type": "compound", "rings": [
            [[0, 0], [1, 0], [2, 0]],
            [[0, 0], [5, 0], [5, 5], [0, 5]]
        ]})


def test_input_geometry_is_never_mutated():
    data = source()
    before = copy.deepcopy(data)
    get_shapes(data)
    assert data == before


def test_invalid_source_does_not_retry_all_packing_attempts(monkeypatch):
    from kiki_layout import engine
    calls=[]
    def invalid(_data, **_kwargs):
        calls.append(1)
        raise ValueError("Object 42: Empty or degenerate closed contour")
    monkeypatch.setattr(engine, "_layout_once", invalid)
    with pytest.raises(ValueError, match="Object 42"):
        engine.layout({"objects":[]}, mode="uniform", trials=8, seed=42)
    assert len(calls)==1
