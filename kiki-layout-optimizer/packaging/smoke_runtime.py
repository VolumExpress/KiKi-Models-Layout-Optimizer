"""Exercise the actual frozen worker end-to-end on synthetic/public geometry."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]


def smoke(payload: Path) -> None:
    payload=payload.resolve()
    worker=payload/'runtime'/('kiki-worker.exe' if sys.platform=='win32' else 'kiki-worker')
    if not worker.is_file():
        raise FileNotFoundError(worker)
    # Place synthetic input inside a real workspace structure; never ship it as user content.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        wd=root/'workspace'/'Smoke_Test'
        wd.mkdir(parents=True)
        source=REPO/'examples'/'synthetic_plate.json'
        shutil.copy2(source,wd/'input_copy.json')
        request=root/'request.json'
        request.write_text(json.dumps({'schema':1,'input':str(wd/'input_copy.json'),
            'options':{'mode':'uniform','families':'named','flow':'free','travel_order':'nearest',
            'rotations':[0],'gap':0.8,'margin':2,'trials':1,'seed':42,'lang':'en',
            'operation':'engrave','kerf_mm':0}}),encoding='utf8')
        done=subprocess.run([str(worker),str(request)],text=True,capture_output=True,timeout=120)
        if done.returncode:
            raise RuntimeError(f'Worker exit {done.returncode}: {done.stdout[-2000:]} {done.stderr[-2000:]}')
        messages=[json.loads(line) for line in done.stdout.splitlines() if line.strip()]
        success=[msg for msg in messages if msg.get('kind')=='complete']
        if not success:
            raise RuntimeError(f'Missing completion receipt: {messages[-5:]}')
        for file in ('result_test.json','preview_test.svg'):
            if not (wd/file).is_file() or not (wd/file).stat().st_size:
                raise RuntimeError(f'Missing output {file}')
        report=success[-1]['report']
        if not report['within_margins'] or report['min_clearance_mm'] < 0.8-1e-3:
            raise RuntimeError(f'Geometry failed validation: {report}')
        print(f"Frozen worker OK: {report['object_count']} objects, minimum gap {report['min_clearance_mm']:.3f} mm")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('payload',type=Path)
    smoke(parser.parse_args().payload)

if __name__=='__main__':main()
