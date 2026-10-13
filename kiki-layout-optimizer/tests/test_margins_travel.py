"""Production-boundary checks and laser travel PROXY tests."""
import json
import math
import subprocess
import sys
from pathlib import Path
import pytest
from shapely.geometry import box
from kiki_layout.engine import layout
from kiki_layout.travel import plan_travel, travel_csv, travel_preview_svg


def specimen():
    return {"document_name":"edge-test.ai", "artboard":{"width_mm":70,"height_mm":48},
            "objects":[
                {"id":str(i),"name":"shape"+str(i),"geometry":{
                    "type":"path","ring":[[0,0],[w,0],[w,h],[0,h]]}}
                for i,(w,h) in enumerate([(6,7),(5,3),(9,2),(3,5),(4,4)])]}


@pytest.mark.parametrize('mode',['dense','uniform','ordered'])
@pytest.mark.parametrize('flow',['free','rows','columns'])
def test_independent_margins_and_flow(mode,flow):
    data=specimen()
    output,geoms=layout(data,mode=mode,flow=flow,gap=.55,margin=0,
                        margin_left=6,margin_top=4,margin_right=8,margin_bottom=3,
                        refine=False)
    margins=output['settings']['margins_mm']
    assert margins=={'left':6,'top':4,'right':8,'bottom':3}
    for geometry in geoms.values():
        l,t,r,b=geometry.bounds
        assert l>=6-1e-5 and t>=4-1e-5
        assert r<=62+1e-5 and b<=45+1e-5
    assert output['report']['travel_proxy']['travel_total_mm']>=0
    assert output['laser_plan']['steps'][0]['number']==1


def test_margin_validation():
    with pytest.raises(ValueError,match='Margins exceed'):
        layout(specimen(),margin_left=40,margin_right=35)
    for val in [-.01,float('nan')]:
        with pytest.raises(ValueError,match='finite'):
            layout(specimen(),margin_left=val)
    with pytest.raises(ValueError,match='flow'):
        layout(specimen(),flow='diagonal')
    with pytest.raises(ValueError,match='travel_order'):
        layout(specimen(),travel_order='zigzag')
    with pytest.raises(ValueError,match='long_jump'):
        layout(specimen(),long_jump_mm=0)


def test_nearest_travel_improves_deliberately_scrambled_source():
    shapes={'d':box(46,0,47,1),'a':box(1,0,2,1),
            'c':box(31,0,32,1),'b':box(16,0,17,1)}
    source=plan_travel(shapes,source_order=['d','a','c','b'],start=(0,0),order='source')
    nearest=plan_travel(shapes,start=(0,0),order='nearest')
    assert nearest['summary']['travel_total_mm']<source['summary']['travel_total_mm']
    assert {x['id'] for x in nearest['steps']}==set(shapes)
    assert nearest['steps'][0]['id']=='a'
    assert len(list(travel_csv(nearest).splitlines()))==5
    result={'artboard':{'width_mm':70,'height_mm':45},
            'settings':{'margins_mm':{'left':2,'top':2,'right':2,'bottom':2}},
            'laser_plan':nearest}
    xml=travel_preview_svg(shapes,result)
    assert '<svg' in xml and 'stroke-dasharray' in xml


def test_row_and_column_plan_covers_all_objects():
    shapes={'one':box(0,0,2,2),'two':box(12,1,14,3),
            'three':box(3,16,5,18),'four':box(15,17,17,19)}
    for order in ('rows','columns','nearest','source'):
        output=plan_travel(shapes,order=order)
        assert len(output['steps'])==4
        assert len(set(k['id'] for k in output['steps']))==4
        assert math.isfinite(output['summary']['travel_total_mm'])


def test_cli_generates_machine_independent_reports(tmp_path):
    src=tmp_path/'input.json';src.write_text(json.dumps(specimen()),encoding='utf-8')
    out=tmp_path/'result.json';svg=tmp_path/'travel.svg';csv=tmp_path/'order.csv'
    result=subprocess.run([sys.executable,'-m','kiki_layout.cli',str(src),
        '-o',str(out),'--gap','0.7','--margin','2','--margin-left','7',
        '--margin-top','4','--margin-right','5','--margin-bottom','3',
        '--flow','rows','--travel-order','nearest','--travel-svg',str(svg),
        '--travel-csv',str(csv),'--no-refine'],capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    output=json.loads(out.read_text(encoding='utf-8'))
    assert output['settings']['margins_mm']['left']==7
    assert csv.is_file() and svg.is_file()
    assert 'travel_total_mm' in output['report']['travel_proxy']
