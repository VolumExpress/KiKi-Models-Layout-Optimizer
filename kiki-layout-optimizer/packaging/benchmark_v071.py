"""Private local benchmark only; P10/P11 vectors are never committed."""
import argparse,json,time,csv,sys
from pathlib import Path
from kiki_layout.engine import layout


def run(inputs, output):
    rows=[]
    for plate,path in inputs.items():
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        for label,weights in [('balanced',dict(area=5,spacing=3.5,travel=1.5)),('area',dict(area=10,spacing=0,travel=0))]:
            t=time.perf_counter()
            result,_=layout(data,mode='uniform',gap=.8,margin=2,rotations=(0,),families='named',
                            flow='free',trials=4,time_budget_sec=60,seed=42,objective_weights=weights)
            report=result['report'];search=report['search']
            rows.append(dict(plate=plate,profile=label,objects=report['object_count'],
                 bbox_mm2=report['occupied_bbox_mm2'],stdev_mm=report['nearest_3_stdev_mm'],
                 min_gap_mm=report['min_clearance_mm'], travel_mm=report['travel_proxy']['travel_total_mm'],
                 pareto=len(search['pareto_frontier']),best=search['best_trial'],attempts=search['completed_trials'],
                 seconds=round(time.perf_counter()-t,3)))
            print(json.dumps(rows[-1]),flush=True)
    with open(output,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Benchmark PRIVATE local exports; they are never uploaded')
    parser.add_argument('--p10',type=Path,required=True)
    parser.add_argument('--p11',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run({'P10':args.p10,'P11':args.p11},args.output)
