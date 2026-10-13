"""Cut placement safety and OS-command selection without Illustrator."""
from pathlib import Path
import pytest
from kiki_layout.engine import layout
from kiki_layout.illustrator_bridge import get_action_command, run_action, IllustratorAutomationError

@pytest.fixture
def sample():
    return {'schema':1,'document_name':'Small.ai',
            'artboard':{'width_mm':55,'height_mm':35},
            'objects':[{'id':str(i),'name':str(i),
                        'geometry':{'type':'path','ring':[[-2,-2],[2,-2],[2,2],[-2,2]]}}
                       for i in range(3)]}

def test_cutting_spacing_adds_kerf_to_material_web(sample):
    result,_=layout(sample,operation='cut',kerf_mm=0.15,gap=0.5,margin=2,
                    families='off',rotations=(0,),mode='dense')
    assert result['settings']['operation']=='cut'
    assert result['settings']['gap_mm']==pytest.approx(0.65)
    assert result['settings']['requested_web_mm']==0.5
    assert result['report']['min_material_web_mm']>=0.5-0.0001
    assert 'CUTTING BETA' in ' '.join(result['report']['warnings'])

def test_engrave_backward_compatible(sample):
    default,_=layout(sample,mode='dense',families='off')
    explicit,_=layout(sample,mode='dense',families='off',operation='engrave',kerf_mm=0)
    assert default['items']==explicit['items']
    assert default['report']['min_clearance_mm']==explicit['report']['min_clearance_mm']

def test_cutting_requires_kerf(sample):
    with pytest.raises(ValueError,match='kerf'):layout(sample,operation='cut',kerf_mm=0)

def test_external_illustrator_commands(tmp_path):
    scripts=tmp_path/'illustrator';scripts.mkdir()
    for name in ('export_selection.jsx','apply_layout.jsx','set_language.jsx'):
        (scripts/name).write_text('alert(1)')
    win=get_action_command('export',platform='win32',root=tmp_path)
    assert win[0]=='cscript.exe' and win[-1].endswith('export_selection.jsx')
    mac=get_action_command('apply',platform='darwin',root=tmp_path)
    assert mac[0]=='osascript' and mac[-1].endswith('apply_layout.jsx')
    with pytest.raises(ValueError):get_action_command('delete',platform='win32',root=tmp_path)

def test_bridge_surfaces_automation_errors(tmp_path):
    p=tmp_path/'illustrator';p.mkdir();(p/'set_language.jsx').touch()
    class Result:
        returncode=3
        stderr='Illustrator not running'
        stdout=''
    with pytest.raises(IllustratorAutomationError,match='not running'):
        run_action('language',platform='win32',root=tmp_path,runner=lambda *a,**k:Result())
