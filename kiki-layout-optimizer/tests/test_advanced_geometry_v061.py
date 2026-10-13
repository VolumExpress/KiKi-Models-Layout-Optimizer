"""Advanced Geometry contract: convex NFP, no unsafe transformations."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.affinity import translate
from kiki_layout.advanced_geometry import convex_no_fit_polygon, nfp_contact_offsets
from kiki_layout.engine import layout


def tiny():
    shapes=[]
    for i,(x,y,w,h) in enumerate([(1,1,4,3),(10,1,2,5),(20,1,6,2),(1,12,5,4),(12,14,2,3)]):
        shapes.append({'id':str(i),'name':f'item-{i}','geometry':{'type':'path','ring':[
            [-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]}})
    return {'document_name':'tiny.ai','source_selection_count':len(shapes),
            'artboard':{'width_mm':36,'height_mm':24},'objects':shapes}


def test_convex_nfp_rectangle_exact_without_clearance():
    fixed=box(10,20,14,23)
    moving=box(-1,-2,2,1)
    nfp=convex_no_fit_polygon(fixed,moving)
    assert nfp.bounds==pytest.approx((8,19,15,25))
    assert nfp.area==pytest.approx(42.)
    assert nfp.covers(translate(moving,9,20).centroid)


def test_convex_nfp_requires_supported_shapes():
    notch=Polygon([(0,0),(5,0),(5,1),(1,1),(1,4),(0,4)])
    assert convex_no_fit_polygon(notch,box(0,0,2,2)) is None
    assert convex_no_fit_polygon(MultiPolygon([box(0,0,1,1),box(2,2,3,3)]),box(0,0,1,1)) is None
    with pytest.raises(ValueError):
        convex_no_fit_polygon(box(0,0,1,1),box(0,0,1,1),-1)


def test_nfp_gap_boundary_candidates_are_collision_checked():
    moving=box(0,0,2,2)
    fixed=box(7,0,9,2)
    pts,n=nfp_contact_offsets(moving,[fixed],.5,reference=(3,0))
    assert n==1 and len(pts)>=4
    assert any(abs(translate(moving,x,y).distance(fixed)-.5)<.02 for x,y in pts)


def test_advanced_geometry_is_opt_in_and_safe():
    data=tiny()
    base,_=layout(data,mode='dense',trials=1,gap=.7,margin=1.5,rotations=(0,),families='off')
    variant,_=layout(data,mode='dense',trials=1,gap=.7,margin=1.5,rotations=(0,),families='off',advanced_geometry=True)
    assert 'advanced_geometry' not in base['report']
    audit=variant['report']['advanced_geometry']
    assert audit['enabled'] and not audit['skipped']
    assert len(variant['items'])==5
    assert variant['report']['min_clearance_mm'] >= .7 - 1e-4
    assert variant['report']['within_margins']
    assert variant['report']['occupied_bbox_mm2'] <= base['report']['occupied_bbox_mm2'] +1e-5


def test_local_repack_off_for_ordered_or_rows():
    for mode,flow in [('ordered','free'),('dense','rows')]:
        r,_=layout(tiny(),mode=mode,flow=flow,gap=.5,margin=1.,advanced_geometry=True)
        assert r['report']['advanced_geometry']['skipped'] is True


def test_reject_non_boolean_advanced_option():
    with pytest.raises(ValueError,match='advanced_geometry'):
        layout(tiny(),advanced_geometry='yes')


def test_local_repack_on_scattered_convex_rectangles_preserves_fixed():
    from kiki_layout.advanced_geometry import local_repack
    source=[box(1,1,4,4),box(16,2,19,5),box(8,13,11,16)]
    adjusted,transform,audit=local_repack(source,[[0.,0.,0.] for _ in source],
                        fixed_count=1,width=30,height=25,margins=(1.,1.,1.,1.),gap=.8)
    original_area=(19-1)*(16-1)
    bounds=[s.bounds for s in adjusted]
    new_area=(max(q[2] for q in bounds)-min(q[0] for q in bounds))*(max(q[3] for q in bounds)-min(q[1] for q in bounds))
    assert new_area < original_area
    assert adjusted[0].equals(source[0])
    assert audit['moves']>=1 and audit['convex_nfp_pairs']>=1
    for i,one in enumerate(adjusted):
        for two in adjusted[i+1:]:assert one.distance(two)>=.8-1e-5


def test_two_member_only_neighbourhood_safe():
    from kiki_layout.advanced_geometry import neighbourhood_repack
    geom=[box(1,1,2,2),box(10,8,11,9)]
    out,tr,stat=neighbourhood_repack(geom,[[0,0,0],[0,0,0]],fixed_count=0,
                width=20,height=15,margins=(1,1,1,1),gap=.8)
    assert len(out)==2 and stat['accepted']==0


def test_single_object_advanced_safe():
    one=tiny();one['objects']=one['objects'][:1];one['source_selection_count']=1
    r,_=layout(one,advanced_geometry=True,mode='dense',gap=.8,margin=1)
    assert r['report']['object_count']==1


def test_cutting_kerf_and_local_geometry():
    r,_=layout(tiny(),advanced_geometry=True,operation='cut',kerf_mm=.2,gap=.5,margin=1)
    assert r['report']['min_clearance_mm']>=.7-1e-5


def test_headless_worker_accepts_geometry_beta(tmp_path):
    from kiki_layout.cep_worker import parse_request
    project=tmp_path/'workspace'/'Example'
    project.mkdir(parents=True)
    (project/'input_copy.json').write_text(json.dumps(tiny()))
    request=tmp_path/'request.json'
    request.write_text(json.dumps({'schema':1,'input':str(project/'input_copy.json'),
                  'options':{'rotations':[0],'advanced_geometry':True,'trials':1}}))
    input_path,options=parse_request(request)
    assert input_path.name=='input_copy.json' and options['advanced_geometry'] is True
    request.write_text(json.dumps({'schema':1,'input':str(project/'input_copy.json'),
                  'options':{'rotations':[0],'advanced_geometry':'true'}}))
    with pytest.raises(ValueError,match='advanced_geometry'):
        parse_request(request)
