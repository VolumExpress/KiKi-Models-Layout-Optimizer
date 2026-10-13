"""Private local benchmark harness: requires P10/P11 JSON outside repo."""
import csv, json, time
from pathlib import Path
from kiki_layout.engine import layout
from kiki_layout.multiobjective import normalized_weights
WEIGHTS={'compact':{'area':10,'spacing':0,'travel':0},
         'balanced':{'area':5,'spacing':3.5,'travel':1.5},
         'travel':{'area':2,'spacing':1,'travel':7}}


def go(files, folder):
    folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for key,file in files.items():
        data=json.loads(Path(file).read_text(encoding='utf-8-sig'))
        begin=time.perf_counter()
        result,_=layout(data,mode='uniform',families='named',flow='free',rotations=(0,),
                        gap=.8,margin=2,trials=4,seed=42,time_budget_sec=75,
                        objective_weights=WEIGHTS['balanced'])
        duration=time.perf_counter()-begin
        trials=result['report']['search']['trial_summaries']
        for trial in trials:
            metrics=trial['metrics']
            rows.append({'plate':key,'trial':trial['trial'],'strategy':trial['strategy'],
                         'bbox_mm2':trial['bbox_mm2'],'stdev_mm':trial['nearest_3_stdev_mm'],
                         'travel_mm':trial['travel_mm'],'area_norm':metrics['area'],
                         'spacing_norm':metrics['spacing'],'travel_norm':metrics['travel'],
                         'actual_duration_sec':round(duration,3)})
        summary={'plate':key,'objects':len(data['objects']),'duration_sec':round(duration,3),
                 'best_trial':result['report']['search']['best_trial'],
                 'pareto_frontier':result['report']['search']['pareto_frontier'],
                 'winners':{}}
        for name,weights in WEIGHTS.items():
            nw=normalized_weights(weights)
            top=min(trials,key=lambda rec:sum(nw[k]*rec['metrics'][k] for k in nw))
            summary['winners'][name]={k:top[k] for k in ['trial','bbox_mm2','nearest_3_stdev_mm','travel_mm']}
        print(json.dumps(summary,ensure_ascii=False),flush=True)
        (folder/f'{key}_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        (folder/f'{key}_weighted_output.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    with (folder/'trial_metrics.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Benchmark private inputs locally; never commit them.')
    parser.add_argument('inputs', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    go({p.stem:p for p in args.inputs}, args.output)
