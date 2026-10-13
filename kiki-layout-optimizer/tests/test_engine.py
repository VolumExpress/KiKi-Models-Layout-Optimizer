import copy
from shapely.affinity import translate,rotate
from kiki_layout.engine import layout
from kiki_layout.geometry import get_shapes
from kiki_layout.families import detect_families


def square(w, h=None, name='A'):
    h=h if h is not None else w
    return {'id':name,'name':name,'geometry':{'type':'path',
            'ring':[[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]}}


def sample():
    motif=[(-1,-1),(1,-1),(1,-.3),(.2,-.3),(.2,1),(-1,1)]
    objs=[]
    for size in (3,5.5,7):
        objs.append({'id':f'm_{size}', 'name':f'Ultramarines__{size}mm',
                     'geometry':{'type':'path','ring':[(x*size/2,y*size/2) for x,y in motif]}})
    objs.extend([square(4,3,'other'),square(6,4,'other2'),square(5,5,'other3')])
    return {'document_name':'test.ai','artboard':{'width_mm':60,'height_mm':40},'objects':objs}


def check_result(src,result,mm_gap):
    orig=get_shapes(src)
    out={i['id']:translate(rotate(orig[i['id']],i['rotation_deg'],origin=(0,0)),
                             i['x_mm'],i['y_mm']) for i in result['items']}
    ids=list(out)
    assert set(ids)==set(orig)
    for j,a in enumerate(ids):
        for b in ids[j+1:]:
            assert out[a].distance(out[b])>=mm_gap-1e-5
    assert result['report']['within_margins']


def test_all_modes_and_rotations():
    src=sample()
    for mode in ('dense','uniform','ordered'):
        result,_=layout(src,mode=mode,gap=.8,margin=2,rotations=(0,90))
        assert result['report']['object_count']==6
        check_result(src,result,.8)


def test_auto_families_recognize_scaled_emblems():
    src=sample()
    labels,warnings=detect_families(src['objects'],get_shapes(src),'auto')
    assert labels['m_3']==labels['m_5.5']==labels['m_7']
    assert warnings
    for mode in ('dense','uniform','ordered'):
        result,_=layout(src,mode=mode,gap=.5,families='auto')
        assert result['report']['cluster_count']<6
        check_result(src,result,.5)


def test_manual_family_names():
    src=sample()
    labels,_=detect_families(src['objects'],get_shapes(src),'named')
    assert labels['m_3']==labels['m_7']
    assert labels['other']!=labels['m_7']


def test_no_source_mutation():
    src=sample(); old=copy.deepcopy(src)
    layout(src,gap=.5)
    assert src==old


def test_impossible_sheet_fails():
    src={'document_name':'x.ai','artboard':{'width_mm':5,'height_mm':5},
         'objects':[square(10,name='too-big')]}
    try: layout(src,gap=1,margin=1)
    except ValueError as e: assert 'Cannot fit' in str(e)
    else: assert False, 'should fail rather than overlap'


def test_reject_unsupported_shape():
    src={'objects':[{'id':'x','geometry':{'type':'image'}}]}
    try: get_shapes(src)
    except ValueError as e: assert 'Unsupported' in str(e)
    else: assert False


def test_true_contour_not_only_bounding_box():
    src={'document_name':'x.ai','artboard':{'width_mm':22,'height_mm':22},'objects':[
        {'id':'L','name':'L','geometry':{'type':'path','ring':[
          [0,0],[10,0],[10,2],[2,2],[2,10],[0,10]]}},
        {'id':'block','name':'block','geometry':{'type':'path','ring':[
          [0,0],[3,0],[3,3],[0,3]]}}]}
    result,geoms=layout(src,mode='dense',gap=1,margin=1)
    check_result(src,result,1)



def test_structured_p10_names_cluster_sizes_not_slots():
    a=square(3,name='P10-SLOT-040__P10-SYM-007__3.0mm__copy01__L1')
    b=square(5.5,name='P10-SLOT-041__P10-SYM-007__5.5mm__copy01__L1')
    c=square(7,name='P10-SLOT-045__P10-SYM-008__7.0mm__copy01__L1')
    a['id']='A';b['id']='B';c['id']='C'
    objects=[a,b,c]
    labels,_=detect_families(objects,get_shapes({'objects':objects}),'named')
    assert labels['A']==labels['B']
    assert labels['A']!=labels['C']


def test_realistic_bounded_candidates():
    from kiki_layout.engine import candidate_positions
    from shapely.geometry import box
    shapes=[box((i%12)*10,(i//12)*10,(i%12)*10+5,(i//12)*10+5) for i in range(60)]
    points=candidate_positions(box(-3,-3,3,3),shapes,145,95,(2,2,2,2),.8)
    assert len(points)<1300, 'avoid quadratic Cartesian explosion for real plates'
    assert (2,2) in points
