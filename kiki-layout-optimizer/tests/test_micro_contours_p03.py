"""Regression for legitimate tiny filled contours in Dark Angels P03.

Individual rings may be much smaller than 1e-7 mm² while the movable
emblem as a whole is substantial. Small positive areas must not be discarded.
"""
import pytest

from kiki_layout.geometry import as_polygon, from_tree, get_shapes


def test_positive_micro_contour_remains_a_polygon():
    # Area: 1e-8 mm², below the previous per-ring 1e-7 cutoff.
    ring = [[0, 0], [0.0002, 0], [0, 0.0001]]
    shape = as_polygon(ring)
    assert not shape.is_empty
    assert shape.area == pytest.approx(1e-8, rel=1e-6)


def test_micro_hole_retained_in_compound_emblem():
    outer = [[0, 0], [4, 0], [4, 4], [0, 4]]
    micro = [[1, 1], [1.0002, 1], [1, 1.0001]]
    obj = {'type': 'compound', 'rings': [outer, micro]}
    shape = from_tree(obj)
    assert shape.area == pytest.approx(16 - 1e-8, abs=2e-12)
    data = {'schema': 1, 'objects': [{'id': 'p03', 'geometry': obj}]}
    assert 'p03' in get_shapes(data)


def test_zero_area_contour_is_still_rejected():
    with pytest.raises(ValueError, match='degenerate'):
        as_polygon([[0, 0], [1, 0], [2, 0]])
