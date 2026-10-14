"""v0.6.4 regression tests for accurate silhouette grouping and LNS safety."""
from kiki_layout.engine import layout
from kiki_layout.geometry import get_shapes, normalized_signature, signature_similarity
from kiki_layout.families import detect_families
from kiki_layout.constraints import save_preset,read_preset
import pytest


def rectangle(name, oid, scale=1., w=4., h=2., change=None):
    points=[[0,0],[w*scale,0],[w*scale,h*scale],[0,h*scale]]
    if change:
        points[2]=[w*scale*.52,h*scale]
    return {'id':str(oid),'name':name,'geometry':{'type':'path','ring':points}}


def test_signature_scale_and_translation_invariant():
    src={'objects':[rectangle('X',0,1),rectangle('X',1,3)]}
    shapes=get_shapes(src)
    assert signature_similarity(normalized_signature(shapes['0']),normalized_signature(shapes['1'])) >= .99


def test_auto_group_not_based_only_on_bbox():
    src={'objects':[rectangle('item-0',0),rectangle('item-1',1,2),rectangle('item-2',2,1,change=True)]}
    shapes=get_shapes(src)
    labels,_=detect_families(src['objects'],shapes,'auto',threshold=.97)
    assert labels['0']==labels['1']
    assert labels['0']!=labels['2']


def test_auto_doesnt_merge_known_different_codes():
    src={'objects':[rectangle('P10-SYM-001__5.5mm',0),rectangle('P10-SYM-002__7mm',1,2)]}
    shapes=get_shapes(src); labels,_=detect_families(src['objects'],shapes,'auto')
    assert labels['0']!=labels['1']


def test_python_lns_leaves_locked_object_and_clearances():
    src={'schema':1,'document_name':'test.ai','source_selection_count':4,
      'artboard':{'width_mm':35,'height_mm':25,'rect_pt':[0,0,35*72/25.4,-25*72/25.4]},
      'objects':[]}
    for i in range(4):
        ob=rectangle('item-'+str(i),i,1,3,3)
        ob['source_bounds_pt']=[i*15,-2,i*15+3*72/25.4,-2-3*72/25.4]
        src['objects'].append(ob)
    first=src['objects'][0]
    rules={'schema':1,'document_name':'test.ai','items':{'0':{'source_name':first['name'],'source_bounds_pt':first['source_bounds_pt'],'lock_position':True,'rotations':[0]}}}
    a,_=layout(src,mode='dense',families='off',gap=.8,margin=1.0,constraints=rules)
    b,_=layout(src,mode='dense',families='off',gap=.8,margin=1.0,constraints=rules,advanced_search=True)
    assert b['report']['occupied_bbox_mm2']<=a['report']['occupied_bbox_mm2']+1e-6
    assert b['report']['min_clearance_mm']>=.8-1e-5
    assert b['report']['locked_count']==1
    pos=lambda result:next((p['x_mm'],p['y_mm']) for p in result['items'] if p['id']=='0')
    assert pos(a)==pos(b)


def test_advanced_search_presets(tmp_path):
    data={'mode':'dense','operation':'engrave','rotations':[0], 'advanced_search':True}
    f=tmp_path/'preset.json';save_preset(f,data)
    assert read_preset(f)['advanced_search'] is True


def test_beam_lns_improves_sparse_synthetic_layout():
    from shapely.geometry import box
    from kiki_layout.lns_search import beam_lns
    from kiki_layout.engine import collision_free
    shapes=[box(x,y,x+3,y+3) for x,y in [(1,1),(19,1),(19,16),(1,16)]]
    before=(max(g.bounds[2] for g in shapes)-min(g.bounds[0] for g in shapes))*(
        max(g.bounds[3] for g in shapes)-min(g.bounds[1] for g in shapes))
    new,_,audit=beam_lns(shapes,[[0,0,0] for _ in shapes],
        fixed_count=0,width=30,height=22,margins=(.5,.5,.5,.5),gap=.5,seed=42)
    after=(max(g.bounds[2] for g in new)-min(g.bounds[0] for g in new))*(
        max(g.bounds[3] for g in new)-min(g.bounds[1] for g in new))
    assert audit['accepted'] and after<before
    assert all(collision_free(g,[h for j,h in enumerate(new) if i!=j],.5) for i,g in enumerate(new))


def test_beam_lns_two_movable_shapes_terminates():
    from shapely.geometry import box
    from kiki_layout.lns_search import beam_lns
    result, _, audit = beam_lns([box(1,1,4,4),box(10,10,13,13)],[[0,0,0],[0,0,0]],
          fixed_count=0,width=25,height=20,margins=(.5,.5,.5,.5),gap=.5)
    assert len(result)==2 and audit['neighbourhoods']<=3
