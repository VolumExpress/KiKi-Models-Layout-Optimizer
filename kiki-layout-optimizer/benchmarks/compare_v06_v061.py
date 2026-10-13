"""Compare v0.6 baseline with Advanced Geometry on exported private JSON.

Usage: python benchmarks/compare_v06_v061.py /path/P10_input_copy.json /path/P11_input_copy.json --output comparison.csv
Does not publish inputs or generated geometry. Never modifies Illustrator files.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
import time
from pathlib import Path

# Run inside editable-install or project root with PYTHONPATH=src.
from kiki_layout.engine import layout


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exported_json',type=Path,nargs='+')
    parser.add_argument('--output',type=Path,default=Path('advanced_geometry_comparison.csv'))
    parser.add_argument('--trials',type=int,default=1)
    parser.add_argument('--gap',type=float,default=.8)
    parser.add_argument('--margin',type=float,default=2)
    args=parser.parse_args(argv)
    results=[]
    for source in args.exported_json:
        data=json.loads(source.read_text(encoding='utf-8-sig'))
        for mode in ('dense','uniform'):
            for advanced in (False,True):
                start=time.perf_counter()
                r,_=layout(data,mode=mode,advanced_geometry=advanced,trials=args.trials,
                           seed=42,gap=args.gap,margin=args.margin,rotations=(0,),families='named',flow='free')
                report=r['report']
                row={'document':data['document_name'],'mode':mode,'advanced_geometry':advanced,
                     'trials':args.trials,'objects':report['object_count'],
                     'bbox_mm2':report['occupied_bbox_mm2'],
                     'stdev_mm':report['nearest_3_stdev_mm'],
                     'min_clearance_mm':report['min_clearance_mm'],
                     'within_margins':report['within_margins'],
                     'time_sec':round(time.perf_counter()-start,3),
                     'accepted':report.get('advanced_geometry',{}).get('accepted','')}
                results.append(row)
                print(f"{source.name} {mode} advanced={advanced}: {row['bbox_mm2']} mm2, {row['time_sec']} s",flush=True)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    with args.output.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    print('Saved',args.output)

if __name__=='__main__':sys.exit(main())
