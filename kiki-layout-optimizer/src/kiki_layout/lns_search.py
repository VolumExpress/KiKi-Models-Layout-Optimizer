"""Bounded, Python-first large-neighbourhood search.

Removes 2-3 WHOLE logical family units, greedily beam-reinserts them into
recomputed free space, and retains only geometrically valid improvements.
Never changes internal family geometry or rotation, nor moves locked units.
This is beam-guided local search, not a globally optimal nesting algorithm.
"""
from __future__ import annotations
import math
import random
import time
from shapely.affinity import translate
from .engine import candidate_positions, collision_free, contained


def _area(shapes):
    if not shapes:
        return 0.
    b=[s.bounds for s in shapes]
    return (max(v[2] for v in b)-min(v[0] for v in b))*(max(v[3] for v in b)-min(v[1] for v in b))


def beam_lns(placed, transforms, *, fixed_count, width, height, margins, gap,
             seed=42, budget_sec=1.5, neighbourhoods=3, beam_width=3):
    """Return new geometries, transforms, audit. Full validation remains in engine.

    An already feasible arrangement is always a candidate, and beam states are
    constructed using the exact, unsimplified Shapely geometry envelopes.
    """
    start=time.monotonic(); deadline=start+budget_sec
    baseline=list(placed); original=[list(t) for t in transforms]
    if len(placed)-fixed_count<2 or budget_sec<=0:
        return baseline,original,{'neighbourhoods':0,'accepted':False,'reason':'too few movable units'}
    n=len(placed); left,top,right,bottom=margins
    rng=random.Random(seed)
    edges=sorted(range(fixed_count,n),key=lambda i: max(placed[i].bounds[2],placed[i].bounds[3]),reverse=True)
    sizes=sorted(range(fixed_count,n),key=lambda i:placed[i].area,reverse=True)
    selections=[]
    for group in (edges[:3], sizes[:3]):
        if len(group)>1 and tuple(group) not in selections: selections.append(tuple(group))
    available=list(range(fixed_count,n))
    tries=0
    while len(selections)<neighbourhoods and tries<neighbourhoods*12:
        tries+=1
        candidate=tuple(rng.sample(available,min(3,len(available))))
        if candidate not in selections: selections.append(candidate)
    attempted=0; accepted=0; best_area=_area(baseline)
    best=baseline; best_transform=original
    for chosen in selections[:neighbourhoods]:
        if time.monotonic()>=deadline:break
        attempted+=1
        fixed=[(i,best[i]) for i in range(n) if i not in chosen]
        # Large blocks first to avoid unreachable intermediate states.
        chosen=sorted(chosen,key=lambda i:-best[i].area)
        states=[(fixed,{})]
        for idx in chosen:
            if time.monotonic()>=deadline:states=[];break
            next_states=[]
            for other,changed in states:
                if time.monotonic()>=deadline:break
                obstacles=[g for _,g in other]
                shape=best[idx]
                x0,y0,x1,y1=shape.bounds
                candidates=candidate_positions(shape,obstacles,width,height,margins,gap)
                # Prioritize positions which reduce the occupied rectangle;
                # explore a bounded number of exact contour checks only.
                base_bounds=[g.bounds for g in obstacles]
                minx=min((b[0] for b in base_bounds),default=left)
                miny=min((b[1] for b in base_bounds),default=top)
                maxx=max((b[2] for b in base_bounds),default=left)
                maxy=max((b[3] for b in base_bounds),default=top)
                def rank(point):
                    x,y=point
                    area=(max(maxx,x+x1-x0)-min(minx,x))* (max(maxy,y+y1-y0)-min(miny,y))
                    return (area,x+y*.0001)
                candidate_pool=sorted(candidates,key=rank)[:70]
                # Keep current valid placement as an option for the beam.
                current=(x0,y0)
                if current not in candidate_pool:candidate_pool.insert(0,current)
                feasible=0
                for x,y in candidate_pool:
                    if time.monotonic()>=deadline:break
                    g=translate(shape,x-x0,y-y0)
                    if not contained(g,width,height,margins) or not collision_free(g,obstacles,gap):continue
                    next_states.append((other+[(idx,g)],dict(changed,**{str(idx):(x-x0,y-y0)})))
                    feasible+=1
                    if feasible>=5:break
            if not next_states:states=[];break
            states=sorted(next_states,key=lambda st:_area([g for _,g in st[0]]))[:beam_width]
        for state, shifts in states:
            by_index={i:g for i,g in state}
            if len(by_index)!=n:continue
            arranged=[by_index[i] for i in range(n)]
            area=_area(arranged)
            if area < best_area-1e-6:
                best_area=area
                best=arranged
                best_transform=[list(t) for t in best_transform]
                for key,(dx,dy) in shifts.items():
                    ix=int(key);best_transform[ix][0]+=dx;best_transform[ix][1]+=dy
                accepted+=1
    return best,best_transform,{
        'neighbourhoods':attempted,'accepted':bool(accepted),'accepted_moves':accepted,
        'elapsed_sec':round(time.monotonic()-start,3),'beam_width':beam_width,
        'budget_sec':budget_sec,'bbox_gain_mm2':round(_area(baseline)-best_area,4)}
