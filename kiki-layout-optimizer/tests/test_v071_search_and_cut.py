import json
from pathlib import Path
import pytest
from shapely.geometry import box
from kiki_layout.multiobjective import construction_score
from kiki_layout.shared_cut_preview import analyze_shared_boundaries,write_preview
from kiki_layout.engine import layout


def sample_data():
    return {
        'schema':1,'document_name':'small.ai','artboard':{'width_mm':35,'height_mm':25},
        'objects':[
            {'id':str(i),'name':'object-'+str(i),
             'source_bounds_pt':[3+i*20,-3,18+i*20,-18],
             'geometry':{'type':'path','ring':[
                 [-2,-2],[-2,2],[2,2],[2,-2]]}}
            for i in range(4)]}


def test_weighted_search_is_full_geometry_checked():
    data=sample_data()
    for weights in [{'area':10,'spacing':0,'travel':0},{'area':0,'spacing':0,'travel':10},{'area':5,'spacing':3,'travel':2}]:
        result,_=layout(data,mode='dense',families='off',gap=.8,margin=1.,trials=3,seed=42,
                        objective_weights=weights,guided_objectives=True)
        assert result['report']['within_margins']
        assert result['report']['min_clearance_mm']>=.8-1e-4
        assert result['report']['search']['pareto_frontier']
        assert result['report']['multiobjective']['construction_guided']


def test_shared_cut_preview_deduplicates_coincident_boundary(tmp_path):
    a=box(0,0,10,10); b=box(10,0,20,10)
    report=analyze_shared_boundaries({'A':a,'B':b})
    assert len(report['shared_edges'])==1
    assert report['shared_total_mm']==10
    assert abs(report['unique_vector_length_mm']-70)<1e-6
    assert report['status']=='DRAFT_NOT_CAM'
    path=tmp_path/'preview.svg';write_preview(report,path,width=30,height=15)
    assert 'NOT FOR CAM' in path.read_text(encoding='utf-8')


def test_shared_cut_preview_refuses_overlap():
    with pytest.raises(ValueError,match='overlap'):
        analyze_shared_boundaries({'A':box(0,0,10,10),'B':box(9,0,20,10)})
