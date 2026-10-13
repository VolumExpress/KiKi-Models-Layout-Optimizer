"""v0.7.2: opt-in matching and navigable size-series layout."""
from __future__ import annotations
import pytest
from shapely.geometry import Polygon
from shapely.affinity import translate,scale
from kiki_layout.families import detect_families
from kiki_layout.engine import layout
from kiki_layout.geometry import get_shapes


def source():
    ring=[[-2,-2],[2,-2],[2,2],[-2,2]]
    obj=[]
    for i,(sym,s) in enumerate([('X',3),('X',5.5),('Y',3),('Y',5.5),('Z',3),('Z',5.5)]):
        ob={'id':str(i),'name':f'Symbol{sym}__{s}mm','geometry':{'type':'path','ring':[[x*s/4,y*s/4] for x,y in ring]}}
        obj.append(ob)
    return {'document_name':'family.ai','artboard':{'width_mm':65,'height_mm':40},'objects':obj}


def test_outline_aware_pairs_varying_stroke_weight():
    # A square frame; same *outer* silhouette, different relative stroke widths.
    objects=[{'id':'a','name':'item-a'},{'id':'b','name':'item-b'}]
    thin=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(.5,.5),(.5,9.5),(9.5,9.5),(9.5,.5)]])
    thick=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(.8,.8),(.8,9.2),(9.2,9.2),(9.2,.8)]])
    shapes={'a':thin,'b':translate(scale(thick,1.7,1.7,origin=(0,0)),3,2)}
    baseline,_=detect_families(objects,shapes,mode='auto')
    improved,warnings=detect_families(objects,shapes,mode='auto',outline_aware=True)
    assert baseline['a'] != baseline['b']
    assert improved['a'] == improved['b']
    assert any('Outline-aware' in w for w in warnings)


def test_outline_aware_preserves_distinct_named_symbols():
    a=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(1,1),(1,9),(9,9),(9,1)]])
    b=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(1.5,1.5),(1.5,8.5),(8.5,8.5),(8.5,1.5)]])
    objs=[{'id':'a','name':'P10-SYM-001__5.5mm'},{'id':'b','name':'P10-SYM-002__7mm'}]
    labels,_=detect_families(objs,{'a':a,'b':b},'auto',outline_aware=True)
    assert labels['a']!=labels['b']


def test_family_first_integrity_and_min_gap():
    data=source()
    result,geo=layout(data,mode='dense',families='named',family_layout='family_first',gap=.8,margin=2,trials=1)
    assert len(result['items'])==6
    assert result['report']['cluster_count']==3
    assert result['report']['min_clearance_mm'] >= .8-1e-5
    assert result['report']['within_margins']
    assert result['settings']['family_layout']=='family_first'
    ids=result['items']
    by_name={item['id']:item['family'] for item in ids}
    for a,b in [('0','1'),('2','3'),('4','5')]:assert by_name[a]==by_name[b]


def test_family_layout_rejects_conflicts_and_preserves_defaults():
    data=source()
    a,_=layout(data,mode='dense',families='named')
    b,_=layout(data,mode='dense',families='named',family_layout='compact')
    assert a==b
    with pytest.raises(ValueError,match='conflicts with strict Ordered'):
        layout(data,mode='ordered',family_layout='family_first')
    with pytest.raises(ValueError,match='family_layout'):
        layout(data,mode='dense',family_layout='nonsense')


def test_cep_worker_accepts_family_options(tmp_path):
    import json
    from kiki_layout.cep_worker import parse_request
    plate=tmp_path/'workspace'/'plate'
    plate.mkdir(parents=True)
    (plate/'input_copy.json').write_text(json.dumps(source()),encoding='utf8')
    request=tmp_path/'req.json'
    request.write_text(json.dumps({'schema':1,'input':str(plate/'input_copy.json'),
        'options':{'rotations':[0],'family_layout':'family_first','outline_aware':True}}))
    _,opts=parse_request(request)
    assert opts['family_layout']=='family_first' and opts['outline_aware'] is True
    opts['outline_aware']='yes'
    request.write_text(json.dumps({'schema':1,'input':str(plate/'input_copy.json'),'options':opts}))
    with pytest.raises(ValueError,match='outline_aware'):
        parse_request(request)


def test_family_preset_roundtrip(tmp_path):
    from kiki_layout.constraints import save_preset,read_preset
    path=tmp_path/'family.json'
    save_preset(path,{'mode':'uniform','operation':'engrave','family_layout':'family_first',
                      'families':'auto','outline_aware':True})
    p=read_preset(path)
    assert p['family_layout']=='family_first' and p['outline_aware'] is True


def test_family_first_locked_object_remains_fixed():
    from test_constraints_v05 import sheet
    src=sheet();fixed=src['objects'][0]
    rules={'schema':1,'document_name':src['document_name'],'items':{'0':{
        'source_name':fixed['name'],'source_bounds_pt':fixed['source_bounds_pt'],
        'lock_position':True,'rotations':[0]}}}
    result,_=layout(src,mode='dense',families='off',family_layout='family_first',
                    constraints=rules,rotations=(0,),gap=.8,margin=2)
    item=next(i for i in result['items'] if i['id']=='0')
    assert (item['x_mm'],item['y_mm'],item['rotation_deg'])==(10.,10.,0)
    assert result['report']['locked_count']==1
