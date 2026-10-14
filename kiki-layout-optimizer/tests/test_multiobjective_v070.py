from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import pytest
from kiki_layout.multiobjective import normalized_weights, metric_vector, weighted_score, frontier
from kiki_layout.engine import layout
from kiki_layout.common_lines import inspect_source_common_edges


def two_adjacent_squares():
    # Artwork sourced in top-left artboard coordinates: squares touch at x=12 mm.
    def one(oid, cx, cy):
        scale=72/25.4
        x0=(cx-2)*scale; x1=(cx+2)*scale
        top=-(cy-2)*scale; bottom=-(cy+2)*scale
        return {'id':str(oid),'name':'square'+str(oid),'uuid':str(oid),
                'source_bounds_pt':[x0,top,x1,bottom],
                'geometry':{'type':'path','ring':[[-2,-2],[2,-2],[2,2],[-2,2]]}}
    return {'schema':1,'document_name':'synthetic_cut.ai','source_selection_count':2,
            'artboard':{'rect_pt':[0,0,145*72/25.4,-95*72/25.4],
                        'width_mm':145,'height_mm':95},
            'objects':[one(0,10,10),one(1,14,10)]}


def test_weights_validation():
    assert normalized_weights({'area':2,'spacing':2,'travel':0}) == {'area':.5,'spacing':.5,'travel':0}
    for invalid in ({'area':0,'spacing':0,'travel':0}, {'area':-1,'spacing':1,'travel':0},
                    {'area':float('nan'),'spacing':2,'travel':1}, {'area':True,'spacing':1,'travel':1},
                    {'area':1,'spacing':1}):
        with pytest.raises(ValueError):normalized_weights(invalid)


def test_frontier_removes_dominated_and_duplicates():
    def r(a,s,t):return {'metrics':{'area':a,'spacing':s,'travel':t}}
    rows=[r(1,1,1),r(2,2,2),r(.8,1.5,1.5),r(1,1,1)]
    assert frontier(rows)==[0,2]


def test_shared_edges_are_inspection_only():
    report=inspect_source_common_edges(two_adjacent_squares())
    assert report['status']=='INSPECTION_ONLY_NOT_CAM'
    assert report['candidate_count']==1
    assert report['candidates'][0]['coincident_length_mm']==pytest.approx(4.)


def test_multiobjective_cut_and_legacy_stability():
    src=two_adjacent_squares()
    args=dict(mode='dense',families='off',rotations=(0,),gap=.8,margin=2)
    old,_=layout(src,**args)
    new,_=layout(src,**args,objective_weights={'area':6,'spacing':2,'travel':2})
    assert old['report']['occupied_bbox_mm2']==new['report']['occupied_bbox_mm2']
    assert new['report']['multiobjective']['selection_only'] is True
    assert new['report']['min_clearance_mm']>=.8-1e-5
    cut,_=layout(src,**args,operation='cut',kerf_mm=.15,cut_common_line_audit=True)
    assert cut['report']['common_line_audit']['candidate_count']==1
    assert cut['report']['min_clearance_mm']>=.95-1e-5
    assert 'common_line_audit' not in old['report']


def test_weighted_multistart_has_report_and_feasible_frontier():
    result,_=layout(two_adjacent_squares(),mode='dense',families='off',gap=.8,
                    rotations=(0,),trials=4,seed=42,
                    objective_weights={'area':2,'spacing':4,'travel':4})
    runs=result['report']['search']
    assert runs['best_trial'] in range(1,5)
    assert runs['pareto_frontier']
    assert all(1<=v<=4 for v in runs['pareto_frontier'])
    assert runs['score']==pytest.approx(weighted_score(result,{'area':2,'spacing':4,'travel':4}),abs=1e-5)


def test_common_line_not_allowed_in_engraving():
    with pytest.raises(ValueError):
        layout(two_adjacent_squares(),operation='engrave',cut_common_line_audit=True)
