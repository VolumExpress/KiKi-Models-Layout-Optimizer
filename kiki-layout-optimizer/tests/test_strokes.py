import math
import pytest
from shapely.geometry import LineString
from kiki_layout.geometry import from_tree, get_shapes
from kiki_layout.engine import layout


def stroke(points, closed=False, width=0.5, cap='round', join='round'):
    return {'type':'stroke','points':points,'closed':closed,'width_mm':width,
            'cap':cap,'join':join,'mitre_limit':5.0}


def test_open_stroke_width_and_endcaps():
    path=stroke([[0,0],[4,0]],width=1,cap='round')
    geom=from_tree(path)
    assert geom.bounds==pytest.approx((-0.5,-0.5,4.5,0.5))
    path['cap']='flat'
    assert from_tree(path).bounds==pytest.approx((0,-0.5,4,0.5))


def test_closed_stroked_line_forms_annulus():
    geom=from_tree(stroke([[0,0],[4,0],[4,4],[0,4]], closed=True, width=.6))
    assert geom.area>0
    assert geom.distance(from_tree({'type':'path','ring':[[1,1],[2,1],[2,2],[1,2]]})) > 0


def test_mixed_fill_and_stroke_area():
    ring=[[0,0],[4,0],[4,4],[0,4]]
    combined=from_tree({'type':'group','children':[
        {'type':'path','ring':ring}, stroke(ring,closed=True,width=.8)]})
    assert combined.area > 16
    assert combined.bounds==pytest.approx((-.4,-.4,4.4,4.4))


def test_compound_hole_and_outline():
    outer=[[0,0],[6,0],[6,6],[0,6]]
    inner=[[2,2],[4,2],[4,4],[2,4]]
    combined=from_tree({'type':'group','children':[
        {'type':'compound','rings':[outer,inner]},
        stroke(inner,closed=True,width=.2)]})
    assert combined.area>32
    assert combined.area<36


def test_invalid_stroke_attributes():
    with pytest.raises(ValueError,match='positive'):
        from_tree(stroke([[0,0],[1,0]],width=0))
    with pytest.raises(ValueError,match='cap'):
        from_tree(stroke([[0,0],[1,0]],cap='unknown'))


def test_solver_respects_stroked_silhouette():
    data={'schema':1,'document_name':'STROKE_TEST.ai','source_selection_count':3,
          'artboard':{'width_mm':30,'height_mm':20},
          'objects':[{'id':'0','name':'outline','geometry':stroke([[0,0],[5,0],[5,5],[0,5]],closed=True,width=1)},
                     {'id':'2','name':'filled','geometry':{'type':'path','ring':[[0,0],[3,0],[3,3],[0,3]]}}]}
    result,geoms=layout(data,mode='dense',gap=.8,margin=1)
    assert result['report']['within_margins']
    assert result['report']['min_clearance_mm']>=.8-1e-4
    assert {i['id'] for i in result['items']} == {'0','2'}
