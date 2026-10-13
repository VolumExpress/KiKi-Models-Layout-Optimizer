"""Small bounded beam destroy/reinsert search for irregular nesting.

Operates on whole family units and respects the frozen prefix. No change to
orientation or within-family offsets. Every move uses real contour validation.
"""
from __future__ import annotations
import time
from shapely.affinity import translate


def _bbox_area(geoms):
    b=[g.bounds for g in geoms]
    return ((max(z[2] for z in b)-min(z[0] for z in b)) *
            (max(z[3] for z in b)-min(z[1] for z in b)))


def beam_neighbourhood_repack(placed, transforms, *, fixed_count,width,height,margins,gap,
                              max_seconds=5., beam_width=3, max_scopes=6,
                              progress=None):
    from .engine import candidate_positions, contained, collision_free
    current=list(placed); changes=[list(t) for t in transforms]
    start=time.monotonic(); attempts=accepted=feasible=0
    if len(current)-fixed_count < 2:
        return current,changes,dict(attempts=0,accepted=0,feasible=0,elapsed_sec=0.)
    movable=list(range(fixed_count,len(current)))
    sorted_edge=sorted(movable,key=lambda i:(current[i].bounds[2]+current[i].bounds[3]),reverse=True)
    scopes=[]
    for idx in sorted_edge[:4]:
        friends=sorted((current[idx].distance(current[j]),j)
                       for j in movable if j!=idx)
        for depth in (2,3):
            scope=tuple([idx]+[j for _,j in friends[:depth-1]])
            if scope not in scopes:scopes.append(scope)
    scopes=scopes[:max_scopes]
    for scope_no,scope in enumerate(scopes):
        if time.monotonic()-start>=max_seconds:break
        attempts+=1
        if progress:progress('compacting',scope_no,len(scopes))
        fixed=[g for i,g in enumerate(current) if i not in scope]
        if not fixed:continue
        # Base keeps all fixed objects, including the locked prefix.
        orders=[tuple(sorted(scope,key=lambda i:current[i].area,reverse=True)),
                tuple(sorted(scope,key=lambda i:current[i].area)),scope]
        original_area=_bbox_area(current)
        best_scope=None
        for order in dict.fromkeys(orders):
            if time.monotonic()-start>=max_seconds:break
            beam=[(fixed,{},0.)]
            for idx in order:
                nxt=[]
                for others,placements,_ in beam:
                    x0,y0,_,_=current[idx].bounds
                    local=translate(current[idx],-x0,-y0)
                    positions=candidate_positions(local,others,width,height,margins,gap)
                    positions.append((x0,y0))
                    bounds=[g.bounds for g in others]
                    minx=min(z[0] for z in bounds);miny=min(z[1] for z in bounds)
                    maxx=max(z[2] for z in bounds);maxy=max(z[3] for z in bounds)
                    w,h=local.bounds[2],local.bounds[3]
                    ranked=[];seen=set()
                    for x,y in positions:
                        key=(round(x,4),round(y,4))
                        if key in seen:continue
                        seen.add(key)
                        if x<margins[0]-1e-5 or y<margins[1]-1e-5 or x+w>width-margins[2]+1e-5 or y+h>height-margins[3]+1e-5:
                            continue
                        area=(max(maxx,x+w)-min(minx,x))*(max(maxy,y+h)-min(miny,y))
                        ranked.append((area,x+y,x,y))
                    ranked.sort()
                    feasible_here=0
                    for _,_,x,y in (ranked[:80] + [(float("inf"),float("inf"),x0,y0)]):
                        if time.monotonic()-start>=max_seconds:break
                        candidate=translate(local,x,y)
                        if not contained(candidate,width,height,margins) or not collision_free(candidate,others,gap):continue
                        new_others=others+[candidate]
                        np={**placements,idx:(candidate,x-x0,y-y0)}
                        nxt.append((new_others,np,_bbox_area(new_others)))
                        feasible_here+=1;feasible+=1
                        if feasible_here>=beam_width:break
                if not nxt:beam=[];break
                beam=sorted(nxt,key=lambda el:(el[2],sum(g.bounds[0]+g.bounds[1] for g in el[0])))[:beam_width]
            for geoms,placements,area in beam:
                if area < original_area-1e-4 and (best_scope is None or area<best_scope[0]):
                    best_scope=(area,placements)
        if best_scope:
            _,placements=best_scope
            for idx,(shape,dx,dy) in placements.items():
                current[idx]=shape
                changes[idx][0]+=dx
                changes[idx][1]+=dy
            accepted+=1
    if progress:progress('compacting',len(scopes),len(scopes))
    return current,changes,dict(attempts=attempts,accepted=accepted,feasible=feasible,
                                 elapsed_sec=round(time.monotonic()-start,3),
                                 soft_limit_reached=time.monotonic()-start>=max_seconds)
