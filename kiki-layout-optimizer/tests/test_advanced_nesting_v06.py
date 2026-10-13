"""The multistart wrapper must be reproducible, collision safe and non-regressing."""
import json
import math
from pathlib import Path
import pytest
from kiki_layout.engine import layout
from kiki_layout.gui_jobs import calculate
from kiki_layout.cep_worker import parse_request
from test_engine import sample, check_result


def test_single_run_matches_baseline_geometry_and_metrics():
    data=sample()
    base,_=layout(data,mode='uniform',gap=.8,margin=2,rotations=(0,))
    explicit,_=layout(data,mode='uniform',gap=.8,margin=2,rotations=(0,),trials=1)
    assert base['items']==explicit['items']
    assert base['report']['occupied_bbox_mm2']==explicit['report']['occupied_bbox_mm2']


def test_multistart_best_score_no_worse_than_first_run():
    data=sample()
    progress=[]
    baseline,_=layout(data,mode='uniform',gap=.8,margin=2,rotations=(0,90),trials=1)
    best,_=layout(data,mode='uniform',gap=.8,margin=2,rotations=(0,90),trials=4,seed=101,
                  progress=lambda *x:progress.append(x))
    check_result(data,best,.8)
    assert best['report']['search']['completed_trials']==4
    assert best['report']['search']['score']<=baseline['report']['search']['score']+1e-5
    assert any(x[0]=='searching' for x in progress)
    assert progress[-1][0]=='complete'


def test_reproducible_trials_and_exact_clearances():
    x,_=layout(sample(),mode='dense',trials=3,seed=23,gap=.5,margin=1,rotations=(0,90))
    y,_=layout(sample(),mode='dense',trials=3,seed=23,gap=.5,margin=1,rotations=(0,90))
    assert x['items']==y['items']
    assert x['report']['search']['trial_summaries']==y['report']['search']['trial_summaries']
    check_result(sample(),x,.5)


def test_contour_anchor_candidates_are_still_fully_validated():
    data=sample()
    x,_=layout(data,mode='dense',trials=2,contour_anchors=True,gap=.8,margin=2,rotations=(0,90))
    check_result(data,x,.8)
    assert x['report']['search']['contour_anchors'] is True


def test_time_budget_soft_stop(monkeypatch):
    from kiki_layout import engine
    # First attempt completes, budget expires before another starts.
    times=iter([0,5,5])
    monkeypatch.setattr(engine.time,'monotonic', lambda:next(times))
    result,_=layout(sample(),trials=5,time_budget_sec=1,mode='dense',gap=.8)
    assert result['report']['search']['completed_trials']==1
    assert result['report']['search']['requested_trials']==5


@pytest.mark.parametrize('kwargs', [{'trials':0},{'trials':31},{'time_budget_sec':-1},
                                     {'time_budget_sec':math.nan},{'seed':True},{'contour_anchors':1}])
def test_reject_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        layout(sample(),**kwargs)


def test_checkpoint_is_separate_from_illustrator_apply(tmp_path):
    base=tmp_path/'workspace'/'Demo';base.mkdir(parents=True)
    p=base/'input_copy.json'
    p.write_text(json.dumps(sample()),encoding='utf8')
    opts={'trials':2,'mode':'dense','gap':.8,'margin':2,'lang':'ru'}
    result,_=calculate(p,opts)
    assert (base/'result_test.json').is_file()
    assert (base/'best_so_far.json').is_file()
    assert (base/'best_so_far.svg').is_file()
    assert result['report']['search']['completed_trials']==2
    # A later single attempt must remove stale intermediate checkpoints.
    calculate(p,{**opts,'trials':1})
    assert not (base/'best_so_far.json').exists()


def test_worker_request_accepts_search_options(tmp_path):
    p=tmp_path/'workspace'/'Doc'/'input_copy.json';p.parent.mkdir(parents=True)
    p.write_text('{}',encoding='utf8')
    req=tmp_path/'request.json'
    req.write_text(json.dumps({'schema':1,'input':str(p),'options':{
        'rotations':[0],'trials':3,'time_budget_sec':35,'seed':42,'contour_anchors':False}}))
    input_path,opts=parse_request(req)
    assert opts['trials']==3
    req.write_text(json.dumps({'schema':1,'input':str(p),'options':{'rotations':[0],'trials':True}}))
    with pytest.raises(ValueError,match='trials'):
        parse_request(req)

def test_multistart_respects_locked_object_and_rotation_rules(tmp_path):
    from test_constraints_v05 import sheet,apply_rules
    data=sheet()
    rules=apply_rules(tmp_path,data,{'0':{'lock_position':True,'rotations':[0]},
                                     '1':{'rotations':[90]}})
    for mode in ('uniform','dense'):
        result,_=layout(data,mode=mode,trials=3,gap=.8,margin=2,rotations=(0,90),constraints=rules)
        items={item['id']:item for item in result['items']}
        assert (items['0']['x_mm'],items['0']['y_mm'],items['0']['rotation_deg'])==(10,10,0)
        assert items['1']['rotation_deg']==90
        assert result['report']['locked_count']==1


def test_multistart_settings_in_portable_presets(tmp_path):
    from kiki_layout.constraints import save_preset,read_preset
    f=tmp_path/'multi.json'
    save_preset(f,{'mode':'dense','operation':'engrave','trials':5,
                   'time_budget_sec':40,'seed':14,'contour_anchors':True})
    x=read_preset(f)
    assert x['trials']==5 and x['contour_anchors'] is True
