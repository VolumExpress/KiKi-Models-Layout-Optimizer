"""Offline matched-config benchmark for bounded generalized NFP.

Usage: python benchmarks/compare_v062.py P10.json P11.json --output comparison.csv
Private input geometry is never published or included in repository archives.
"""
import argparse,csv,json,time
from pathlib import Path
from kiki_layout.engine import layout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,default=Path('v062_benchmark.csv'))
    parser.add_argument('--trials',type=int,default=1)
    args=parser.parse_args()
    rows=[]
    for path in args.inputs:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        for mode in ('dense','uniform'):
            for advanced in (False,True):
                t=time.monotonic()
                result,_=layout(data,mode=mode,gap=.8,margin=2.,rotations=(0,),families='named',
                                trials=args.trials,seed=42,advanced_geometry=advanced)
                report=result['report'];stat=report.get('advanced_geometry') or {}
                rows.append(dict(input=path.name,document=data.get('document_name',''),mode=mode,
                    trials=args.trials,advanced_geometry=advanced,objects=report['object_count'],
                    bbox_mm2=report['occupied_bbox_mm2'],stdev_mm=report['nearest_3_stdev_mm'],
                    min_clearance_mm=report['min_clearance_mm'],within_margins=report['within_margins'],
                    nfp_pairs=stat.get('constructive_nfp_pairs',0)+stat.get('general_nfp_pairs',0),
                    seconds=round(time.monotonic()-t,3)))
                print(rows[-1],flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':main()
