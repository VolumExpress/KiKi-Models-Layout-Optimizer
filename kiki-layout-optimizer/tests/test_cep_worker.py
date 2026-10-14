"""Headless CEP calculations must not start Tk or read an arbitrary command."""
import json
from pathlib import Path
import pytest
from kiki_layout.cep_worker import parse_request, run


def test_reject_wrong_workspace(tmp_path):
    f=tmp_path/'request.json'
    f.write_text(json.dumps({'schema':1,'input':str(tmp_path/'input_copy.json'),
        'options':{'rotations':[0]}}),encoding='utf8')
    with pytest.raises(ValueError,match='workspace'):
        parse_request(f)


def test_reject_extra_option(tmp_path):
    input_file=tmp_path/'workspace'/'Doc'/'input_copy.json'
    input_file.parent.mkdir(parents=True)
    input_file.write_text('{}',encoding='utf8')
    f=tmp_path/'request.json'
    f.write_text(json.dumps({'schema':1,'input':str(input_file),
        'options':{'rotations':[0],'command':'cmd.exe'}}))
    with pytest.raises(ValueError,match='Unsupported'):
        parse_request(f)


def test_worker_demo_progress(tmp_path, capsys):
    from kiki_layout.gui_jobs import project_root
    example=project_root()/'examples'/'synthetic_plate.json'
    input_file=tmp_path/'workspace'/'Demo'/'input_copy.json'
    input_file.parent.mkdir(parents=True)
    input_file.write_text(example.read_text(encoding='utf8'),encoding='utf8')
    request=tmp_path/'req.json'
    request.write_text(json.dumps({'schema':1,'input':str(input_file),
        'options':{'mode':'dense','gap':0.8,'margin':0,'margin_left':2,
        'margin_top':2,'margin_right':2,'margin_bottom':2,
        'rotations':[0],'families':'off','flow':'free','travel_order':'nearest',
        'operation':'engrave','kerf_mm':0,'lang':'ru'}}),encoding='utf8')
    run(request)
    events=[json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert events[0]['kind']=='started'
    assert any(x['kind']=='progress' for x in events)
    assert events[-1]['kind']=='complete'
    assert events[-1]['report']['within_margins'] is True
    for name in ('result_test.json','preview_test.svg','route_test.svg','route_test.csv'):
        assert (input_file.parent/name).is_file()
