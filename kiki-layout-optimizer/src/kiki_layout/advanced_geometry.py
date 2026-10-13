"""v0.6.2 opt-in geometry refinement.

Bounded generalized polygon NFP anchors, plus safe
whole-unit relocation. Unsupported high-complexity concave/multi-part shapes use heuristic anchors.
Every proposed placement is checked against original contour geometry by
Shapely before acceptance; callers perform a complete post-pass audit.

This is not a general concave NFP engine or a machine CAM toolpath generator.
"""
from __future__ import annotations

import math
import time
from shapely.affinity import translate
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry.base import BaseGeometry
from .general_nfp import nfp_boundary_candidates


def _convex_vertices(shape: BaseGeometry, limit: int = 36):
    """Return polygon corners iff polygon is simple, truly convex, and small."""
    if not isinstance(shape, Polygon) or shape.interiors or shape.is_empty:
        return None
    coords = list(shape.exterior.coords)[:-1]
    if len(coords) < 3 or len(coords) > limit:
        return None
    hull = shape.convex_hull
    if abs(hull.area - shape.area) > 1e-7 * max(1., shape.area):
        return None
    return coords


def convex_no_fit_polygon(fixed: BaseGeometry, moving: BaseGeometry, clearance: float = 0.):
    """Exact Minkowski NFP for convex polygons BEFORE optional gap buffering.

    Reference point for the moving shape is the origin. For a fixed polygon A
    and moving polygon B, prohibited translations are A + (-B).
    Convex hull of all vertex sums is exact for convex A/B. clearance > 0 uses
    a Shapely circular buffer approximating an arc (not an exact analytic disk).
    Returns None if either shape is concave, has holes or is not Polygon.
    """
    a = _convex_vertices(fixed)
    b = _convex_vertices(moving)
    if a is None or b is None:
        return None
    if not math.isfinite(clearance) or clearance < 0:
        raise ValueError('clearance must be a finite nonnegative number')
    nfp = MultiPoint([(x-u, y-v) for x,y in a for u,v in b]).convex_hull
    return nfp.buffer(clearance, quad_segs=8) if clearance else nfp


def nfp_contact_offsets(moving, neighbours, gap, limit_neighbours=4, max_samples=16, reference=(0.,0.)):
    """Bounded *general* NFP anchors incl. concave / multipart silhouettes.

    Exact for polygonal surfaces under the triangulation/pair caps. The returned
    samples are not exhaustive: callers must validate against original shapes.
    Shapes beyond the limits are safely skipped, not approximated as convex.
    """
    candidates=[]; used=0
    at_reference=translate(moving,reference[0],reference[1])
    ranked=sorted(neighbours,key=lambda g:at_reference.distance(g))[:min(8,len(neighbours))]
    for fixed in ranked:
        if used >= limit_neighbours: break
        anchors,exact=nfp_boundary_candidates(fixed,moving,gap,
                         max_samples=max_samples,complexity=36,max_pairs=120)
        if not exact:continue
        used+=1
        candidates.extend(anchors)
    return candidates,used


def _footprint(candidate, others):
    bounds=[g.bounds for g in others]+[candidate.bounds]
    return ((max(b[2] for b in bounds)-min(b[0] for b in bounds)) *
            (max(b[3] for b in bounds)-min(b[1] for b in bounds)))


def local_repack(placed, transforms, *, fixed_count, width, height, margins,
                 gap, max_passes=2, nfp=True, progress=None, max_seconds=9., max_units=16):
    """Monotone, bounded coordinate descent over whole logical family units.

    Only strictly reduces global unit bounding-box area. The calling engine
    later compares the ORIGINAL per-object mode score to the unmodified layout
    and rolls back if necessary (e.g. Uniform regularity got worse).
    """
    from .engine import candidate_positions, contained, collision_free
    current=list(placed)
    changes=[list(x) for x in transforms]
    number_candidates=0; accepted=0; nfp_pairs=0
    limit_reached=False
    usable=range(fixed_count,len(current))
    if not list(usable):
        return current,changes,{'moves':0,'candidate_checks':0,'general_nfp_pairs':0,'convex_nfp_pairs':0,'passes':0}
    t0=time.monotonic()
    passes_done=0
    for repeat in range(max_passes):
        passes_done+=1
        moved=False
        # Prioritize objects near right/bottom exposed boundaries.
        indices=sorted(usable,key=lambda i: (current[i].bounds[2]+current[i].bounds[3]),reverse=True)[:max_units]
        for idx,i in enumerate(indices):
            if time.monotonic()-t0 > max_seconds:
                limit_reached=True
                break
            if progress: progress('compacting', repeat*len(indices)+idx, max_passes*len(indices))
            original=current[i]
            others=current[:i]+current[i+1:]
            if not others: continue
            base_minx,base_miny,_,_=original.bounds
            local=translate(original,-base_minx,-base_miny)
            from .engine import candidate_positions
            positions=candidate_positions(local,others,width,height,margins,gap)
            if nfp:
                offsets,count=nfp_contact_offsets(local,others,gap,reference=(base_minx,base_miny))
                nfp_pairs+=count
                positions.extend(offsets)
            old_area=_footprint(original,others)
            xlim=width-margins[2]-(local.bounds[2]-local.bounds[0])
            ylim=height-margins[3]-(local.bounds[3]-local.bounds[1])
            seen=set(); ranked=[]
            other_bounds=[g.bounds for g in others]
            min_ox=min(b[0] for b in other_bounds)
            min_oy=min(b[1] for b in other_bounds)
            max_ox=max(b[2] for b in other_bounds)
            max_oy=max(b[3] for b in other_bounds)
            local_w=local.bounds[2]; local_h=local.bounds[3]
            for x,y in positions:
                k=(round(x,4),round(y,4))
                if k in seen: continue
                seen.add(k)
                if x < margins[0]-1e-5 or y < margins[1]-1e-5 or x > xlim+1e-5 or y > ylim+1e-5:
                    continue
                # Cheap rectangle-based upper bound; only the best placements
                # need expensive true shape collision evaluation.
                w=max(x+local_w,max_ox)-min(x,min_ox)
                h=max(y+local_h,max_oy)-min(y,min_oy)
                area=w*h
                if area <= old_area+1e-5:
                    # Secondary compactness helps edge objects move inward even
                    # when several unrelated objects currently define the bbox.
                    ranked.append((area, x+y, x, y))
            ranked.sort(key=lambda p: (p[0],p[1],p[3],p[2]))
            # Limit to 60 exact checks per object and pass on complex artwork.
            for _,_,x,y in ranked[:40]:
                number_candidates+=1
                cand=translate(local,x,y)
                if not contained(cand,width,height,margins) or not collision_free(cand,others,gap):
                    continue
                area=_footprint(cand,others)
                # Accept better area or equal area + top-left advancement.
                origin_progress=original.bounds[0]+original.bounds[1]
                cand_progress=cand.bounds[0]+cand.bounds[1]
                if area+1e-5<old_area or (area<=old_area+1e-5 and cand_progress<origin_progress-0.1):
                    current[i]=cand
                    changes[i][0] += x-base_minx
                    changes[i][1] += y-base_miny
                    accepted+=1; moved=True
                    break
        if limit_reached or not moved: break
    if progress: progress('compacting', max_passes*len(list(usable)), max_passes*len(list(usable)))
    return current,changes,{'moves':accepted,'candidate_checks':number_candidates,
                            'general_nfp_pairs':nfp_pairs,'convex_nfp_pairs':nfp_pairs,'passes':passes_done,'soft_limit_reached':limit_reached,
                            'elapsed_sec':round(time.monotonic()-t0,3)}


def neighbourhood_repack(placed, transforms, *, fixed_count, width, height, margins,
                         gap, max_seconds=7., max_neighbourhoods=8, progress=None):
    """Small destroy-and-repair search: remove 2-3 islands and reinsert them.

    This can escape the situation where two edge shapes jointly block every
    single-object footprint improvement. No rotations or family-internal
    geometry are changed. If no improving fully legal repair is found, return
    exactly the original layout.
    """
    from .engine import candidate_positions, collision_free, contained
    if len(placed)-fixed_count < 2:
        return list(placed),[list(t) for t in transforms],{'attempts':0,'accepted':0}
    start=time.monotonic()
    current=list(placed); moved=[list(t) for t in transforms]
    total_attempts=0; accepted=0
    indices=list(range(fixed_count,len(placed)))
    # Right/bottom extremes are useful seeds; deterministic repeatability.
    extreme=sorted(indices,key=lambda i:current[i].bounds[2]+current[i].bounds[3],reverse=True)
    scopes=[]
    for offset in (0,1,2,3):
        near=extreme[offset:offset+3]
        if len(near)>=2:
            scopes.append(tuple(near))
    for i in extreme[:3]:
        distances=sorted((current[i].distance(current[j]),j) for j in indices if j!=i)
        scopes.append(tuple([i]+[j for _,j in distances[:2]]))
    scopes=list(dict.fromkeys(scopes))[:max_neighbourhoods]
    initial_area=_footprint(current[0],current[1:])
    for n,scope in enumerate(scopes):
        if time.monotonic()-start>max_seconds: break
        total_attempts+=1
        if progress: progress('compacting',n,len(scopes))
        base=[current[i] for i in range(len(current)) if i not in scope]
        if not base: continue
        # Try two distinct insertion orders per removed neighbourhood.
        for order in [sorted(scope,key=lambda i:current[i].area,reverse=True),
                      sorted(scope,key=lambda i:current[i].area)]:
            others=list(base); placement={}; valid=True
            for idx in order:
                shape=current[idx]
                x0,y0,_,_=shape.bounds
                local=translate(shape,-x0,-y0)
                positions=candidate_positions(local,others,width,height,margins,gap)
                # Preserve feasibility option if the exact source slot is free.
                positions.append((x0,y0))
                b=[g.bounds for g in others]
                minx,miny=min(q[0] for q in b),min(q[1] for q in b)
                maxx,maxy=max(q[2] for q in b),max(q[3] for q in b)
                w,h=local.bounds[2],local.bounds[3]
                unique=set(); ranked=[]
                for x,y in positions:
                    key=(round(x,4),round(y,4))
                    if key in unique:continue
                    unique.add(key)
                    if x < margins[0]-1e-5 or y < margins[1]-1e-5 or x+w > width-margins[2]+1e-5 or y+h > height-margins[3]+1e-5:
                        continue
                    area=(max(maxx,x+w)-min(minx,x))*(max(maxy,y+h)-min(miny,y))
                    ranked.append((area,x+y,x,y))
                ranked.sort()
                best=None
                for _,_,x,y in ranked[:35]:
                    cand=translate(local,x,y)
                    if contained(cand,width,height,margins) and collision_free(cand,others,gap):
                        best=(cand,x-x0,y-y0)
                        break
                if best is None:
                    valid=False;break
                placement[idx]=best
                others.append(best[0])
            if not valid: continue
            area=_footprint(others[0],others[1:])
            if area < initial_area-1e-4:
                for idx,(shape,dx,dy) in placement.items():
                    current[idx]=shape
                    moved[idx][0]+=dx; moved[idx][1]+=dy
                accepted+=1
                initial_area=area
                break
    if progress: progress('compacting',len(scopes),len(scopes))
    return current,moved,{'attempts':total_attempts,'accepted':accepted,
                          'elapsed_sec':round(time.monotonic()-start,3)}
