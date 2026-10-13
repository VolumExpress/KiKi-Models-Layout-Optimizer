from kiki_layout.engine import layout
from kiki_layout.object_editor import human_label


def test_engine_carries_uuid_through_layout():
    sample = {'document_name':'Test.ai','source_selection_count':1,
              'artboard':{'width_mm':40,'height_mm':30},
              'objects':[{'id':'0','name':'item-0','uuid':'abc-uuid',
                          'source_bounds_pt':[0,10,10,0],
                          'geometry':{'type':'path','ring':[[-2,-2],[2,-2],[2,2],[-2,2]]}}]}
    result, _ = layout(sample)
    assert result['items'][0]['source_uuid'] == 'abc-uuid'


def test_editor_friendly_names_and_dimensions():
    obj={'id':'14','name':'P10-SLOT-046__P10-SYM-007__9.0mm__L1',
         'source_bounds_pt':[0,10,28.3465,-10]}
    label,dim=human_label(obj)
    assert 'P10-SYM-007' in label
    assert '9,0 мм' in label
    assert '10.0 × 7.1' in dim
    unnamed={'id':'32','name':'item-32','source_bounds_pt':[0,10,10,0]}
    assert 'Без имени · #32' in human_label(unnamed)[0]
