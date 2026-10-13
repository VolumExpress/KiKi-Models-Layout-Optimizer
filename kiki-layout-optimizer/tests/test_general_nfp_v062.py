"""Geometry correctness independent of whether the placement heuristic improves."""
import math
import pytest
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.affinity import translate
from kiki_layout.general_nfp import general_no_fit_polygon, nfp_boundary_candidates
from kiki_layout.beam_repack import beam_neighbourhood_repack

@pytest.mark.parametrize('fixed,moving', [
    (Polygon([(0,0),(7,0),(7,1),(1,1),(1,7),(0,7)]),box(-.6,-.6,.6,.6)),
    (box(0,0,8,8).difference(box(2,2,6,6)), box(-.5,-.5,.5,.5)),
    (MultiPolygon([box(0,0,2,2),box(6,0,8,2)]), box(-.5,-.5,.5,.5)),
    (Polygon([(0,0),(5,0),(5,5),(3,5),(3,2),(2,2),(2,5),(0,5)]),
     Polygon([(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)])),
])
def test_concave_holes_multipart_nfp_membership(fixed,moving):
    obstacle=general_no_fit_polygon(fixed,moving)
    assert obstacle is not None
    for xx in [x*.5 for x in range(-4,24)]:
        for yy in [y*.5 for y in range(-4,24)]:
            shifted=translate(moving,xx,yy)
            # Boundary contact can count as collision under covers, sample only
            # interiors away from numerically ambiguous tangent positions.
            if abs(fixed.distance(shifted)) < 1e-8 and fixed.intersection(shifted).area < 1e-8:
                continue
            collision=fixed.intersection(shifted).area>1e-8
            inside=obstacle.contains(__import__('shapely').geometry.Point(xx,yy))
            assert collision == inside,(xx,yy,collision,inside)

def test_hole_allows_small_shape_not_large():
    ring=box(0,0,10,10).difference(box(2,2,8,8))
    small=box(-.5,-.5,.5,.5)
    big=box(-4,-4,4,4)
    assert not general_no_fit_polygon(ring,small).covers(__import__('shapely').geometry.Point(5,5))
    assert general_no_fit_polygon(ring,big).covers(__import__('shapely').geometry.Point(5,5))

def test_clearance_and_certified_budget():
    concave=Polygon([(0,0),(4,0),(4,1),(1,1),(1,4),(0,4)])
    square=box(-.2,-.2,.2,.2)
    ob=general_no_fit_polygon(concave,square,0.8)
    assert ob is not None
    assert ob.covers(__import__('shapely').geometry.Point(4.6,0.5))
    assert general_no_fit_polygon(concave,square,max_pairs=1) is None
    with pytest.raises(ValueError): general_no_fit_polygon(concave,square,-.1)

def test_beam_preserves_locked_and_legality():
    placed=[box(1,1,4,4),box(20,1,23,4),box(5,16,8,19),box(15,17,18,20)]
    result,changes,stats=beam_neighbourhood_repack(placed,[[0.,0.,0.] for _ in placed],
        fixed_count=1,width=30,height=24,margins=(1,1,1,1),gap=.8,max_seconds=3)
    assert result[0].equals(placed[0])
    assert len(result)==len(placed)
    assert stats['attempts']>=1
    for i,g in enumerate(result):
        assert g.bounds[0]>=1-1e-5 and g.bounds[2]<=29+1e-5
        for other in result[i+1:]:assert g.distance(other)>=.8-1e-5
