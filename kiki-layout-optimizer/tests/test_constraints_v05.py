import copy
import json
import pytest
from pathlib import Path
from kiki_layout.engine import layout
from kiki_layout.constraints import (save_constraints, read_constraints, validate_constraints,
                                     save_preset, read_preset)

MM = 72.0/25.4

def piece(oid, x, y, size=3, name=None):
    return dict(id=oid,name=name or ('name_'+oid),
       geometry={'type':'path','ring':[[-size/2,-size/2],[size/2,-size/2],[size/2,size/2],[-size/2,size/2]]},
       source_bounds_pt=[(x-size/2)*MM,-(y-size/2)*MM,(x+size/2)*MM,-(y+size/2)*MM])

def sheet():
    return {'document_name':'Test.ai','source_selection_count':3,
            'artboard':{'width_mm':60,'height_mm':40,'rect_pt':[0,0,60*MM,-40*MM]},
            'objects':[piece('0',10,10),piece('1',24,11),piece('2',38,12)]}

def apply_rules(tmp_path, src, modifications):
    path=tmp_path/'input_copy.json'
    path.write_text(json.dumps(src),encoding='utf-8')
    save_constraints(path,src,modifications)
    return read_constraints(path)

def test_fixed_position_survives_uniform_refine(tmp_path):
    src=sheet()
    before=copy.deepcopy(src)
    rules=apply_rules(tmp_path,src,{'0':{'lock_position':True, 'rotations':[0]}})
    result,geoms=layout(src,gap=.8,margin=2,rotations=(0,90),constraints=rules)
    a=next(i for i in result['items'] if i['id']=='0')
    assert (a['x_mm'],a['y_mm'],a['rotation_deg']) == (10,10,0)
    assert result['report']['locked_count']==1
    assert result['settings']['locked_ids']==['0']
    assert src==before

def test_individual_rotation_enforced(tmp_path):
    src=sheet()
    rules=apply_rules(tmp_path,src,{'1':{'rotations':[90]}})
    result,_=layout(src,rotations=(0,90,180),constraints=rules,mode='dense')
    assert next(i for i in result['items'] if i['id']=='1')['rotation_deg']==90
    assert result['report']['individual_rotation_count']==1

def test_global_and_individual_incompatible_fails(tmp_path):
    src=sheet()
    rules=apply_rules(tmp_path,src,{'1':{'rotations':[90]}})
    with pytest.raises(ValueError,match='no rotation allowed'):
        layout(src,rotations=(0,180),constraints=rules)

def test_anchored_objects_too_close_rejected(tmp_path):
    src=sheet();src['objects'][1]=piece('1',12,10)
    rules=apply_rules(tmp_path,src,{'0':{'lock_position':True},'1':{'lock_position':True}})
    with pytest.raises(ValueError,match='conflicts'):
        layout(src,gap=1.0,constraints=rules)

def test_fixed_object_outside_margins(tmp_path):
    src=sheet();src['objects'][0]=piece('0',2,2)
    rules=apply_rules(tmp_path,src,{'0':{'lock_position':True}})
    with pytest.raises(ValueError,match='outside'):
        layout(src,margin=2,constraints=rules)

def test_old_export_requires_rect_for_locks(tmp_path):
    src=sheet();src['artboard'].pop('rect_pt')
    rules=apply_rules(tmp_path,src,{'0':{'lock_position':True}})
    with pytest.raises(ValueError,match='fresh export'):
        layout(src,constraints=rules)

def test_name_and_geometry_fingerprint_fails_closed(tmp_path):
    src=sheet();rules=apply_rules(tmp_path,src,{'0':{'rotations':[0]}})
    src['objects'][0]['source_bounds_pt'][0]+=1
    with pytest.raises(ValueError,match='changed its bounds'):
        layout(src,constraints=rules)
    src=sheet();src['document_name']='SomethingElse.ai'
    with pytest.raises(ValueError,match='another Illustrator document'):
        layout(src,constraints=rules)

def test_constraints_do_not_merge_locked_family(tmp_path):
    src=sheet()
    src['objects'][0]['name']='P10-SLOT-000__P10-SYM-007__3mm'
    src['objects'][1]['name']='P10-SLOT-001__P10-SYM-007__5.5mm'
    rules=apply_rules(tmp_path,src,{'0':{'lock_position':True}})
    result,_=layout(src,constraints=rules,families='named',gap=.8)
    assert next(i for i in result['items'] if i['id']=='0')['family']=='locked:0'
    assert next(i for i in result['items'] if i['id']=='0')['x_mm']==10

def test_save_load_global_preset_no_geometry(tmp_path):
    path=tmp_path/'presets'/'laser.json'
    save_preset(path,{'mode':'uniform','operation':'cut','gap':.7,'kerf_mm':.15,
                      'rotations':(0,180),'secret_geometry':'not stored'})
    data=read_preset(path)
    assert data['rotations']==[0,180]
    assert 'secret_geometry' not in data
    assert data['operation']=='cut'

def test_preset_does_not_accept_unsupported_fields(tmp_path):
    path=tmp_path/'invalid.json'
    path.write_text(json.dumps({'schema':1,'options':{'mode':'dense','operation':'engrave','command':'rm -rf'}}))
    with pytest.raises(ValueError,match='Unsupported'):
        read_preset(path)


def test_incompatible_member_rotation_splits_family(tmp_path):
    src=sheet()
    src['objects'][0]['name']='P10-SLOT-000__P10-SYM-007__3mm'
    src['objects'][1]['name']='P10-SLOT-001__P10-SYM-007__5.5mm'
    rules=apply_rules(tmp_path,src,{'0':{'rotations':[0]},'1':{'rotations':[90]}})
    result,_=layout(src,constraints=rules,rotations=(0,90),families='named',gap=.8)
    a={i['id']:i for i in result['items']}
    assert a['0']['rotation_deg']==0
    assert a['1']['rotation_deg']==90
    assert a['0']['family'] != a['1']['family']
    assert any('split' in w for w in result['report']['warnings'])
