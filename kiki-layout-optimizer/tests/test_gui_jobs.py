"""GUI persistence and workspace tests without starting a graphical session."""
import json
from pathlib import Path
from kiki_layout.gui_jobs import document_slug, workspace_for, available_exports, calculate


def test_workspace_paths_cross_platform(tmp_path):
    assert document_slug('P10_TEST_Layout.ai') == 'P10_TEST_Layout'
    assert document_slug('A:/B\\C?.ai') == 'A__B_C_'
    assert workspace_for('P10_TEST_Layout.ai', tmp_path) == tmp_path/'workspace'/'P10_TEST_Layout'


def test_autocalculation_writes_all_artifacts(tmp_path):
    folder = workspace_for('Test.ai',tmp_path)
    folder.mkdir(parents=True)
    data={
      'schema':1,'document_name':'Test.ai','source_selection_count':2,
      'artboard':{'width_mm':30,'height_mm':20},
      'objects':[
          {'id':'0','name':'one','geometry':{'type':'path','ring':[[-2,-2],[2,-2],[2,2],[-2,2]]}},
          {'id':'1','name':'two','geometry':{'type':'path','ring':[[-1,-1],[1,-1],[1,1],[-1,1]]}},
      ]}
    export=folder/'input_copy.json'
    export.write_text(json.dumps(data),encoding='utf-8')
    assert available_exports(tmp_path)==[export]
    result,geoms=calculate(export,dict(mode='uniform',gap=0.8,margin=0,
          margin_left=2,margin_top=2,margin_right=3,margin_bottom=4,
          rotations=(0,),families='off',flow='free',travel_order='nearest',lang='ru'))
    assert result['report']['object_count']==2
    assert result['report']['within_margins']
    assert set(geoms)=={'0','1'}
    for file in ['result_test.json','preview_test.svg','route_test.svg','route_test.csv']:
        assert (folder/file).stat().st_size>10
    assert not (folder/'result_test.tmp').exists()
    assert json.loads((folder/'result_test.json').read_text())['document_name']=='Test.ai'
    assert '<svg' in (folder/'preview_test.svg').read_text()


def test_real_progress_reports_phases(tmp_path):
    folder=workspace_for('Progress.ai',tmp_path)
    folder.mkdir(parents=True)
    data={'schema':1,'document_name':'Progress.ai','artboard':{'width_mm':40,'height_mm':25},
          'objects':[{'id':str(i),'name':'shape'+str(i),
                      'geometry':{'type':'path','ring':[[-2,-2],[2,-2],[2,2],[-2,2]]}}
                     for i in range(3)]}
    filename=folder/'input_copy.json'
    filename.write_text(json.dumps(data),encoding='utf-8')
    updates=[]
    calculate(filename,dict(mode='uniform',gap=0.8,margin=2,
         families='off',rotations=(0,),flow='free',travel_order='nearest'),
         progress=lambda stage,done,total:updates.append((stage,done,total)))
    assert updates[0][0]=='preparing'
    assert updates[-1]==('complete',1,1)
    assert any(stage=='placing' and n==3 and done==3 for stage,done,n in updates)
    assert any(stage=='refining' for stage,done,n in updates)
    assert any(stage=='validating' for stage,done,n in updates)
