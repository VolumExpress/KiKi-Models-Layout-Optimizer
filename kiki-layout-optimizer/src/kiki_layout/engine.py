"""Deterministic, collision-safe constructive irregular nesting prototype.

This is a heuristic, not proof of globally optimal packing or uniformity.
It checks actual contour distances, not just bounding boxes.
"""
from __future__ import annotations
import math
import statistics
import random
import time
from shapely.affinity import rotate, translate
from .geometry import get_shapes
from .families import detect_families, build_units
from .constraints import validate_constraints, source_centre_mm

EPS = 1e-5


def bounds_near(a, b, margin):
    x0,y0,x1,y1 = a.bounds
    u0,v0,u1,v1 = b.bounds
    return not (x1 + margin < u0 or u1 + margin < x0 or y1 + margin < v0 or v1 + margin < y0)


def collision_free(candidate, taken, gap):
    for other in taken:
        if bounds_near(candidate, other, gap) and candidate.distance(other) < gap - EPS:
            return False
    return True


def contained(shape, width, height, margins):
    left, top, right, bottom = margins
    x0, y0, x1, y1 = shape.bounds
    return (x0 >= left-EPS and y0 >= top-EPS
            and x1 <= width-right+EPS and y1 <= height-bottom+EPS)


def rotation_vector(x,y, degrees):
    a=math.radians(degrees)
    return (x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a))


def candidate_positions(shape, taken, width, height, margins, gap, contour_anchors=False):
    """Bounded deterministic contour-nesting placement candidates.

    The original full x-by-y Cartesian product scales quadratically in the
    number of previous objects and becomes unusably slow on actual P10.
    Combine boundary anchors, perimeter-neighbour anchors and a bounded grid.
    These are heuristic candidates, not an exhaustive global optimum.
    """
    x0, y0, x1, y1 = shape.bounds
    w, h = x1-x0, y1-y0
    left, top, right, bottom = margins
    xmax, ymax = width-right-w, height-bottom-h
    xs, ys = {left, xmax}, {top, ymax}
    pairs = [(left,top), (xmax,top), (left,ymax), (xmax,ymax)]
    for placed in taken:
        l,t,r,b = placed.bounds
        px = (l,r+gap,r-w,l-w-gap,(l+r-w)/2)
        py = (t,b+gap,b-h,t-h-gap,(t+b-h)/2)
        xs.update(px); ys.update(py)
        # Adjacent on any side, edge-aligned and centred; individual islands
        # can exploit irregular holes even if their bounding boxes overlap.
        pairs.extend(((r+gap,t),(r+gap,b-h),(l-w-gap,t),(l-w-gap,b-h),
                      (l,b+gap),(r-w,b+gap),(l,t-h-gap),(r-w,t-h-gap),
                      (l,t),(r-w,t),(l,b-h),(r-w,b-h),
                      ((l+r-w)/2,b+gap),((l+r-w)/2,t-h-gap),
                      (r+gap,(t+b-h)/2),(l-w-gap,(t+b-h)/2)))
    if contour_anchors and taken:
        # EXPERIMENTAL vertex-contact anchors: sparse approximation to positions
        # sampled on the configuration-space obstacle boundary. This is NOT an
        # exact No-Fit Polygon/Minkowski sum. Every candidate still passes the
        # original exact Shapely collision and clearance tests.
        def extreme_points(g):
            result=[]
            shapes_list=list(g.geoms) if hasattr(g,'geoms') else [g]
            for part in shapes_list:
                if not hasattr(part,'exterior'): continue
                coords=list(part.exterior.coords)
                if len(coords)<3: continue
                result.extend((min(coords,key=lambda p:p[0]),max(coords,key=lambda p:p[0]),
                               min(coords,key=lambda p:p[1]),max(coords,key=lambda p:p[1])))
            return list(dict.fromkeys((round(x,5),round(y,5)) for x,y in result))[:8]
        # Bound expensive offset curves by a small sample of already placed
        # shapes. The final complete validation is unchanged.
        moving=extreme_points(shape)
        for placed in taken[-8:]:
            obstacle=placed.buffer(gap, quad_segs=2, join_style=2)
            anchors=extreme_points(obstacle)
            for ax,ay in anchors[:6]:
                for vx,vy in moving[:6]:
                    pairs.append((ax-vx+x0, ay-vy+y0))
    xs = sorted(x for x in xs if left-EPS <= x <= xmax+EPS)
    ys = sorted(y for y in ys if top-EPS <= y <= ymax+EPS)
    # Up to a 13x13 grid, spread over every observed contour anchor.
    def sample(vs, limit=13):
        if len(vs)<=limit: return vs
        return [vs[round(i*(len(vs)-1)/(limit-1))] for i in range(limit)]
    pairs.extend((x,y) for x in sample(xs) for y in sample(ys))
    seen=set(); result=[]
    for x,y in pairs:
        if not (left-EPS <= x <= xmax+EPS and top-EPS <= y <= ymax+EPS):
            continue
        key=(round(x,5),round(y,5))
        if key not in seen:
            seen.add(key); result.append((x,y))
    return result


def min_neighbour_distances(geometries, k=3):
    distances = []
    for i, a in enumerate(geometries):
        d = sorted(a.distance(b) for j,b in enumerate(geometries) if i!=j)
        distances.extend(d[:k])
    return distances


def _layout_once(data, *, mode="uniform", gap=0.8, margin=2.0,
           margin_left=None, margin_top=None, margin_right=None, margin_bottom=None,
           flow="free", travel_order="nearest", long_jump_mm=15.0,
           rotations=(0,), families="off", family_threshold=0.97, outline_aware=False,
           width=None, height=None, refine=True, progress=None,
           operation="engrave", kerf_mm=0.0, constraints=None,
           order_strategy="baseline", random_seed=42, contour_anchors=False, candidate_policy="default", advanced_geometry=False, advanced_search=False, search_weights=None, family_layout="compact"):
    if family_layout not in ("compact", "family_first"):
        raise ValueError("family_layout must be compact or family_first")
    if family_layout == "family_first" and mode == "ordered":
        raise ValueError("Family-first placement conflicts with strict Ordered mode")
    if operation not in ("engrave", "cut"):
        raise ValueError("operation must be engrave or cut")
    kerf_mm=float(kerf_mm)
    if not math.isfinite(kerf_mm) or kerf_mm < 0 or (operation == "cut" and kerf_mm <= 0):
        raise ValueError("Cutting requires a positive finite kerf_mm")
    requested_gap=float(gap)
    # Nominal contours must remain at least kerf + material-web apart.
    # This is conservative separation for NON-SHARED cutting contours.
    if operation == "cut":
        gap=requested_gap+kerf_mm
    if mode not in ("dense","uniform","ordered"):
        raise ValueError("Invalid mode")
    if flow not in ("free", "rows", "columns"):
        raise ValueError("flow must be free, rows or columns")
    if travel_order not in ("source", "nearest", "rows", "columns"):
        raise ValueError("travel_order must be source, nearest, rows or columns")
    margins = tuple(float(margin if v is None else v) for v in
                    (margin_left, margin_top, margin_right, margin_bottom))
    if not math.isfinite(gap) or gap < 0 or any(not math.isfinite(v) or v < 0 for v in margins):
        raise ValueError("gap and margins must be finite and >= 0")
    left, top, right, bottom = margins
    board=data.get("artboard",{})
    width = float(width if width is not None else board.get("width_mm",145))
    height = float(height if height is not None else board.get("height_mm",95))
    if width <= left + right or height <= top + bottom:
        raise ValueError("Margins exceed sheet size")
    if not rotations or any(v not in (0,90,180,270) for v in rotations):
        raise ValueError("Prototype supports rotation values 0, 90, 180, 270 only")
    if len(set(rotations))!=len(rotations):
        rotations = tuple(dict.fromkeys(rotations))
    def update(stage, completed, total):
        if progress is not None:
            progress(stage, completed, total)
    update("preparing", 0, 1)
    shapes=get_shapes(data)
    objects=data["objects"]
    rules=validate_constraints(data,constraints)
    locked_ids={oid for oid,rule in rules.items() if rule['lock_position']}
    allowed={}
    for obj in objects:
        oid=str(obj['id'])
        rule=rules.get(oid,{})
        per_object=rule.get('rotations')
        angles=(0,) if oid in locked_ids else tuple(a for a in rotations if per_object is None or a in per_object)
        if not angles:
            raise ValueError(f'Object {oid}: no rotation allowed by both global and individual settings')
        allowed[oid]=angles
    labels,warnings=detect_families(objects,shapes,families,family_threshold,outline_aware=outline_aware)
    # Locked objects are anchored independently and must never become movable
    # members of a detected family. A family with incompatible rotations is
    # broken into independent islands rather than silently violating a rule.
    family_members={}
    for oid,label in labels.items():
        if oid in locked_ids:
            labels[oid]='locked:'+oid
        else:
            family_members.setdefault(label,[]).append(oid)
    for label,ids_in_family in family_members.items():
        joint=set(allowed[ids_in_family[0]])
        for oid in ids_in_family[1:]: joint.intersection_update(allowed[oid])
        if not joint:
            for oid in ids_in_family: labels[oid]='rotation:'+oid
            warnings.append(f'Family {label}: split because members have incompatible rotation limits')
    family_entries={}
    for ob in objects:
        oid=str(ob['id']);family_entries.setdefault(labels[oid],[]).append(oid)
    family_audit=[]
    for label,group_ids in family_entries.items():
        if len(group_ids)<2: continue
        members=[]
        for oid in group_ids:
            shape=shapes[oid]; x0,y0,x1,y1=shape.bounds
            ob=next(v for v in objects if str(v['id'])==oid)
            members.append({'id':oid,'name':ob.get('name',''),
                'equivalent_mm':round(math.sqrt((x1-x0)*(y1-y0)),2)})
        family_audit.append({'label':label,'members':members})
    units=build_units(objects,shapes,labels,gap,max_group_width=max(20.,(width-left-right)*0.55))

    # v0.7.2: optional user-directed family-first sequencing.
    # Never change the default compact algorithm.
    if family_layout == "family_first":
        from .family_layout import visual_style
        for u in units: u["visual_style"] = visual_style(u, shapes)
    fixed_units=[u for u in units if any(oid in locked_ids for oid in u['ids'])]
    movable_units=[u for u in units if not any(oid in locked_ids for oid in u['ids'])]
    units=movable_units
    if family_layout == "family_first":
        from .family_layout import sort_family_units
        units=sort_family_units(units,shapes,strategy=order_strategy,seed=random_seed)
    if mode == "ordered":
        # Stable order based on original user selection (first family occurrence).
        order={str(ob["id"]):i for i,ob in enumerate(objects)}
        units.sort(key=lambda u:min(order[o] for o in u["ids"]))
    elif family_layout == "family_first":
        pass  # sorted into visual sections by sort_family_units above
    else:
        # Reordering is permitted only for modes without a strict source-order rule.
        # First attempt retains the fully backwards-compatible baseline.
        rng = random.Random(random_seed)
        if order_strategy == "baseline":
            units.sort(key=lambda u: -u["geometry"].area)
        elif order_strategy == "perimeter":
            units.sort(key=lambda u: -u["geometry"].length)
        elif order_strategy == "max_dimension":
            units.sort(key=lambda u: -max(u["geometry"].bounds[2]-u["geometry"].bounds[0],
                                              u["geometry"].bounds[3]-u["geometry"].bounds[1]))
        elif order_strategy == "shuffled":
            # Diversified but reproducible; size is a gentle prior, not a constraint.
            decorated=[(-u["geometry"].area * rng.uniform(.6, 1.4),rng.random(),u) for u in units]
            decorated.sort(key=lambda item:(item[0],item[1]))
            units=[v[2] for v in decorated]
        else:
            raise ValueError("Unknown trial ordering")

    placed=[]
    transforms=[]
    constructive_nfp_pairs=0
    constructive_nfp_start=time.monotonic() if advanced_geometry else 0.
    object_by_id={str(ob['id']):ob for ob in objects}
    for fixed in fixed_units:
        oid=fixed['ids'][0]
        fx,fy=source_centre_mm(object_by_id[oid],data)
        fixed_geometry=translate(fixed['geometry'],fx,fy)
        if not contained(fixed_geometry,width,height,margins):
            raise ValueError(f'Locked object {oid} is outside the requested margins')
        if not collision_free(fixed_geometry,placed,gap):
            raise ValueError(f'Locked object {oid} conflicts with another fixed object at the requested gap')
        placed.append(fixed_geometry)
        transforms.append([fx,fy,0])
    fixed_count=len(placed)
    shelf_cursor=(left,top,0.)
    previous_style=None
    shelf_fallbacks=0
    units=fixed_units+units
    update("placing", 0, len(units)-fixed_count)
    for unit_index, unit in enumerate(units[fixed_count:]):
        best=None
        permitted=set(allowed[unit['ids'][0]])
        for oid in unit['ids'][1:]: permitted.intersection_update(allowed[oid])
        shelf_slot=None
        if family_layout == "family_first":
            from .family_layout import next_shelf_candidate
            style=unit.get("visual_style", "mixed")
            base_cursor=shelf_cursor
            # A continuous shelf keeps visual-style blocks consecutive without
            # wasting a complete row whenever the style changes.
            for angle in rotations:
                if angle not in permitted: continue
                rotated=rotate(unit["geometry"],angle,origin=(0,0))
                slot=next_shelf_candidate(rotated,placed,width,height,margins,gap,
                    base_cursor,collision_free,contained)
                if slot is None: continue
                shape,dx,dy,position=slot
                # Prefer preserving the Illustrator orientation where possible.
                score=(shape.bounds[1]-top)*100000+(shape.bounds[0]-left)*100+int(angle!=0)*10000
                if shelf_slot is None or score<shelf_slot[0]:
                    shelf_slot=(score,shape,dx,dy,angle,position)
        if shelf_slot is not None:
            _,geo,dx,dy,angle,shelf_cursor=shelf_slot
            placed.append(geo)
            transforms.append([dx,dy,angle])
            previous_style=unit.get("visual_style","mixed")
            update("placing",unit_index+1,len(units)-fixed_count)
            continue
        if family_layout == "family_first":
            shelf_fallbacks += 1
        for angle in rotations:
            if angle not in permitted: continue
            rotated=rotate(unit["geometry"],angle,origin=(0,0))
            xmin,ymin,xmax,ymax=rotated.bounds
            positions=candidate_positions(rotated,placed,width,height,margins,gap, contour_anchors=contour_anchors)
            if (advanced_geometry and flow == 'free' and mode != 'ordered'
                    and placed and time.monotonic()-constructive_nfp_start < 1.5):
                from .advanced_geometry import nfp_contact_offsets
                anchors, used=nfp_contact_offsets(rotated,placed,gap,
                    limit_neighbours=2,max_samples=12,reference=(0.,0.))
                constructive_nfp_pairs+=used
                positions.extend((x+xmin,y+ymin) for x,y in anchors)
            for x,y in positions:
                dx,dy=x-xmin,y-ymin
                cand=translate(rotated,dx,dy)
                if not contained(cand,width,height,margins) or not collision_free(cand,placed,gap):
                    continue
                # Compact footprint primary; anchor tie-breaker supports predictable layouts.
                far_right=max([p.bounds[2] for p in placed]+[cand.bounds[2]])
                far_bottom=max([p.bounds[3] for p in placed]+[cand.bounds[3]])
                current_w=max(EPS,far_right-left)
                current_h=max(EPS,far_bottom-top)
                footprint=current_w*current_h
                aspect_error=abs(math.log((current_w/current_h)/(width/height)))
                aspect_weight={"dense":0.10,"uniform":0.10,"ordered":0.35}[mode]
                if candidate_policy == 'balanced': aspect_weight *= 2.5
                elif candidate_policy == 'footprint': aspect_weight = 0.
                score=footprint*(1+aspect_weight*aspect_error)+0.03*y+0.01*x
                # Optional constructive scanline-style packing. This rearranges
                # physical islands and does NOT control galvo hatching or machine paths.
                if flow == "rows":
                    score=(y-top)*width*10 + (x-left)
                elif flow == "columns":
                    score=(x-left)*height*10 + (y-top)
                # v0.7.1: search weights influence construction, not just final
                # selection.  Cheap bounding-box clearance is a RANKING proxy;
                # every placement still passes exact GEOS contour checks.
                if search_weights is not None and flow == 'free' and mode != 'ordered':
                    from .multiobjective import construction_score
                    score = construction_score(cand, placed, gap, width, height,
                                               footprint, (left, top), search_weights)
                if best is None or score < best[0]-1e-8:
                    best=(score,cand,dx,dy,angle)
        if best is None:
            raise ValueError(f"Cannot fit family {unit['family']!r} onto plate with gap {gap} mm")
        _,geo,dx,dy,angle=best
        placed.append(geo)
        transforms.append([dx,dy,angle])
        if family_layout == "family_first":
            a,b,c,d=geo.bounds
            shelf_cursor=(c+gap,b,max(shelf_cursor[2] if b==shelf_cursor[1] else 0.,d-b))
            previous_style=unit.get("visual_style","mixed")
        update("placing", unit_index+1, len(units)-fixed_count)

    if mode=="uniform" and refine and len(placed)>1:
        # Local-search objective is bounded for real plates containing 50-200
        # complex emblems. Use exact silhouette distance for likely neighbours,
        # with bounding-box lower bounds to avoid costly distant comparisons.
        def nearest_three(candidate, neighbours):
            bx0, by0, bx1, by1 = candidate.bounds
            ranked=[]
            for neighbour in neighbours:
                nx0,ny0,nx1,ny1=neighbour.bounds
                sep_x=max(0.,nx0-bx1,bx0-nx1)
                sep_y=max(0.,ny0-by1,by0-ny1)
                ranked.append((math.hypot(sep_x,sep_y),neighbour))
            ranked.sort(key=lambda p:p[0])
            nearest=[]
            for min_possible,other in ranked:
                if len(nearest)>=3 and min_possible >= nearest[-1]:
                    break
                actual=candidate.distance(other)
                nearest.append(actual)
                nearest.sort()
                if len(nearest)>3:
                    nearest.pop()
            return nearest

        def local_uniform_objective(candidate, others):
            near=nearest_three(candidate,others)
            if not near: return 0.0
            # Penalise gaps much larger than the requested minimum and local
            # variation. Layout footprint is a secondary objective.
            gaps=[min(15.,d) for d in near]
            residual=statistics.mean((d-gap)**2 for d in gaps)
            variance=statistics.pvariance(gaps) if len(gaps)>1 else 0.
            xmax=max([candidate.bounds[2]]+[g.bounds[2] for g in others])
            ymax=max([candidate.bounds[3]]+[g.bounds[3] for g in others])
            return 0.65*residual + 1.2*variance + 0.0003*(xmax-left)*(ymax-top)

        steps = (0.5, 0.25) if len(placed)>32 else (1.0, 0.5, 0.25)
        passes = 1 if len(placed)>32 else 3
        refinements = len(steps)*passes*(len(placed)-fixed_count)
        refine_done = 0
        update("refining", 0, refinements)
        for step in steps:
            for _ in range(passes):
                moved=False
                for i in reversed(range(fixed_count, len(placed))):
                    refine_done += 1
                    update("refining", refine_done, refinements)
                    original=placed[i]
                    other_placed=placed[:i]+placed[i+1:]
                    best_obj=local_uniform_objective(original,other_placed)
                    best_shape=original
                    best_shift=(0.,0.)
                    for ox,oy in ((step,0),(-step,0),(0,step),(0,-step),
                                  (step,step),(step,-step),(-step,step),(-step,-step)):
                        cand=translate(original,ox,oy)
                        if not contained(cand,width,height,margins):
                            continue
                        if not collision_free(cand,other_placed,gap):
                            continue
                        obj=local_uniform_objective(cand,other_placed)
                        if obj < best_obj-1e-7:
                            best_obj,best_shape,best_shift=obj,cand,(ox,oy)
                    if best_shift!=(0.,0.):
                        placed[i]=best_shape
                        transforms[i][0]+=best_shift[0]
                        transforms[i][1]+=best_shift[1]
                        moved=True
                if not moved:
                    break

    geometry_audit = None
    search_audit = None
    if advanced_search and flow == "free" and mode != "ordered":
        from .lns_search import beam_lns
        update("compacting",0,1)
        before=[list(t) for t in transforms]
        initial=list(placed)
        def exact_search_score(trans):
            actual=[]
            for u,(dx,dy,angle) in zip(units,trans):
                for oid in u['ids']:
                    ox,oy=u['offsets'][oid]
                    rx,ry=rotation_vector(ox,oy,angle)
                    actual.append(translate(rotate(shapes[oid],angle,origin=(0,0)),dx+rx,dy+ry))
            bbox=[g.bounds for g in actual]
            area=(max(q[2] for q in bbox)-min(q[0] for q in bbox))*(max(q[3] for q in bbox)-min(q[1] for q in bbox))/(width*height)
            if mode=='dense':return area
            dd=min_neighbour_distances(actual)
            spread=statistics.pstdev(dd) if dd else 0.
            excess=max(0.,(statistics.mean(dd) if dd else gap)-gap)
            unit_gap=max(gap,.5)
            return .60*area+.30*spread/unit_gap+.10*excess/unit_gap
        prior_score=exact_search_score(before)
        placed,transforms,search_audit=beam_lns(placed,transforms,
            fixed_count=fixed_count,width=width,height=height,margins=margins,
            gap=gap,seed=random_seed,budget_sec=1.25)
        # LNS must never be allowed to worsen the heuristic footprint.
        after_score=exact_search_score(transforms)
        search_audit['objective_gain']=round(prior_score-after_score,7)
        if after_score>=prior_score-1e-10:
            placed,transforms=initial,before
            search_audit['accepted']=False
            search_audit['reason']='No verified improvement in the selected mode'
        update("compacting",1,1)
    elif advanced_search:
        search_audit={"skipped":True,"reason":"Strict row/column/ordered placement"}
    if advanced_geometry:
        if flow != "free" or mode == "ordered":
            geometry_audit = {"enabled": True, "skipped": True,
                "reason": "Constrained row/column or source ordering: local repack disabled"}
        else:
            from .advanced_geometry import local_repack
            from .beam_repack import beam_neighbourhood_repack
            pre_placed=list(placed)
            pre_transforms=[x[:] for x in transforms]
            update("compacting",0,2)
            repacked, adjusted, stats=local_repack(placed, transforms,
                fixed_count=fixed_count,width=width,height=height,margins=margins,
                gap=gap)
            update("compacting",1,2)
            # No spatial improvement or a malformed move never reaches output.
            placed, transforms = repacked, adjusted
            placed, transforms, neighbourhood = beam_neighbourhood_repack(
                placed,transforms,fixed_count=fixed_count,width=width,height=height,
                margins=margins,gap=gap)
            update("compacting",2,2)
            geometry_audit={"enabled":True,"skipped":False, **stats,
                            "beam_neighbourhood":neighbourhood,
                            "original_placed":pre_placed,
                            "constructive_nfp_pairs":constructive_nfp_pairs,
                            "original_transforms":pre_transforms}

    if geometry_audit is not None and not geometry_audit.get("skipped"):
        # Compare full per-object objective (not proxy family hull footprint).
        def exact_mode_score(packed_transforms):
            all_geoms=[]
            for u,(dx,dy,a) in zip(units,packed_transforms):
                for oid in u['ids']:
                    ox,oy=u['offsets'][oid]
                    rx,ry=rotation_vector(ox,oy,a)
                    all_geoms.append(translate(rotate(shapes[oid],a,origin=(0,0)),dx+rx,dy+ry))
            b=[g.bounds for g in all_geoms]
            area=(max(v[2] for v in b)-min(v[0] for v in b))*(max(v[3] for v in b)-min(v[1] for v in b))
            if mode == 'dense': return area/(width*height)
            distances=min_neighbour_distances(all_geoms)
            spread=statistics.pstdev(distances) if distances else 0.
            mean=statistics.mean(distances) if distances else gap
            unit_gap=max(gap,.5)
            return (.60*area/(width*height) + .30*spread/unit_gap +
                    .10*max(0.,mean-gap)/unit_gap)
        baseline_transforms=geometry_audit.pop('original_transforms')
        oldscore=exact_mode_score(baseline_transforms)
        current_score=exact_mode_score(transforms)
        if current_score > oldscore - 1e-10:
            placed=geometry_audit.pop('original_placed')
            transforms=baseline_transforms
            # pre_transforms popped above, need keep to restore
            # restored later via local variable
            geometry_audit['accepted']=False
        else:
            geometry_audit.pop('original_placed')
            geometry_audit['accepted']=True
        geometry_audit['baseline_mode_score']=round(oldscore,7)
        geometry_audit['candidate_mode_score']=round(current_score,7)

    update("validating", 0, 1)
    source_by_id={str(ob["id"]):ob for ob in objects}
    output=[]
    for unit,(dx,dy,angle) in zip(units,transforms):
        for oid in unit["ids"]:
            ox,oy=unit["offsets"][oid]
            rx,ry=rotation_vector(ox,oy,angle)
            source=source_by_id[oid]
            output.append({"id":oid,"x_mm":round(dx+rx,6),"y_mm":round(dy+ry,6),
                           "rotation_deg":angle,"family":unit["family"],
                           "source_name":source.get("name"),"source_uuid":source.get("uuid"),
                           "source_bounds_pt":source.get("source_bounds_pt")})

    # FULL geometric validation on every original member, not just unit hull.
    transformed={}
    for item in output:
        g=rotate(shapes[item["id"]],item["rotation_deg"],origin=(0,0))
        transformed[item["id"]]=translate(g,item["x_mm"],item["y_mm"])
    ids=list(transformed)
    pairwise=[]
    for i,one in enumerate(ids):
        for two in ids[i+1:]:
            d=transformed[one].distance(transformed[two])
            pairwise.append((one,two,d))
            if d < gap - EPS:
                raise AssertionError(f"Gap violation: {one}/{two} = {d:.6f} mm")
    for oid,g in transformed.items():
        if not contained(g,width,height,margins):
            raise AssertionError(f"Object outside margins: {oid}")
    nearest=min_neighbour_distances(list(transformed.values()))
    min_clearance=min((d for _,_,d in pairwise),default=None)
    if transformed:
        xmax=max(g.bounds[2] for g in transformed.values())
        ymax=max(g.bounds[3] for g in transformed.values())
        xmin=min(g.bounds[0] for g in transformed.values())
        ymin=min(g.bounds[1] for g in transformed.values())
    else:
        xmin=ymin=xmax=ymax=0
    from .travel import plan_travel
    # Proxy assumes a single marking unit per selected object and jump points at
    # representative interior/centroid coordinates. Actual hatch and machine
    # firmware determine real laser travel and processing time.
    laser_plan=plan_travel(transformed, source_order=[str(o["id"]) for o in objects],
                           order=travel_order, start=(left,top), long_jump_mm=long_jump_mm)
    report={"object_count":len(ids),"cluster_count":len(units),
            "family_audit":family_audit,
            "family_layout": {"mode":family_layout,"shelf_fallbacks":shelf_fallbacks,
                              "description":"Visual-style ordered rigid families on compact shelves" if family_layout=="family_first" else "Legacy compact geometry"},
            "pair_count":len(pairwise),
            "locked_count":len(locked_ids),
            "individual_rotation_count":sum(r.get("rotations") is not None for r in rules.values()),
            "min_clearance_mm":round(min_clearance,5) if min_clearance is not None else None,
            "min_material_web_mm":(round(max(0.0,min_clearance-kerf_mm),5)
                                   if operation == 'cut' and min_clearance is not None else None),
            "nearest_3_mean_mm":round(statistics.mean(nearest),5) if nearest else None,
            "nearest_3_stdev_mm":round(statistics.pstdev(nearest),5) if nearest else None,
            "silhouette_area_mm2":round(sum(g.area for g in transformed.values()),3),
            "occupied_bbox_mm2":round((xmax-xmin)*(ymax-ymin),3),
            "plate_area_mm2":round(width*height,3),
            "within_margins":True,
            "edge_clearances_mm":{
                "left":round(xmin,5),"top":round(ymin,5),
                "right":round(width-xmax,5),"bottom":round(height-ymax,5)},
            "travel_proxy":laser_plan["summary"],
            "warnings":warnings+(["CUTTING BETA: kerf-aware separation only; no common-line merging, inner-before-outer CAM, tabs or toolpath. Never cut straight from this preview."] if operation == "cut" else [])+["Polyline-based contour approximation; inspect native Illustrator geometry before fabrication.", "Laser jumps are CENTROID-PROXY estimates, not controller toolpaths or time savings."]}
    if geometry_audit is not None:
        report['advanced_geometry']=geometry_audit
    if search_audit is not None:
        report['advanced_search']=search_audit
    update("complete", 1, 1)
    return {"schema":1,"document_name":data.get("document_name",""),
            "source_selection_count":data.get("source_selection_count",len(objects)),
            "artboard":{"width_mm":width,"height_mm":height},
            "settings":{"mode":mode,"operation":operation,"kerf_mm":kerf_mm,
                        "requested_web_mm":requested_gap if operation == "cut" else None,
                        "gap_mm":gap,"margin_mm":margin,
                        "margins_mm":{"left":left,"top":top,"right":right,"bottom":bottom},
                        "flow":flow,"family_layout":family_layout,"travel_order":travel_order,
                        "long_jump_mm":long_jump_mm,
                        "rotations_deg":list(rotations),"families":families,"outline_aware":outline_aware,
                        "constraints_applied":bool(rules),"locked_ids":sorted(locked_ids),
                        "advanced_geometry":advanced_geometry,"advanced_search":advanced_search},
            "items":output,"laser_plan":laser_plan,"report":report},transformed


def _solution_score(result, mode, objective_weights=None):
    if objective_weights is not None:
        from .multiobjective import weighted_score
        return weighted_score(result, objective_weights)
    """Dimensionless comparison within one fixed plate and gap configuration."""
    report = result["report"]
    plate = max(report["plate_area_mm2"], EPS)
    area = report["occupied_bbox_mm2"] / plate
    if mode == "dense":
        return area
    if mode == "ordered":
        # Ordered trials retain original sequence, and score only compactness.
        return area
    # Uniform is multi-objective: footprint, spread of three nearest
    # clearance distances and their excess over the mandated minimum.
    gap = max(float(result["settings"]["gap_mm"]), .5)
    spread = (report["nearest_3_stdev_mm"] or 0.) / gap
    excess = max(0., (report["nearest_3_mean_mm"] or gap) - gap) / gap
    return .60 * area + .30 * spread + .10 * excess


def layout(data, *, trials=1, time_budget_sec=0., seed=42,
           contour_anchors=False, advanced_geometry=False, advanced_search=False,
           objective_weights=None, guided_objectives=False, cut_common_line_audit=False, on_best=None, on_trial=None, progress=None, **kwargs):
    """Anytime bounded multi-start around the validated contour-safe solver.

    trials=1 is the exact v0.5.2 behavior (unless contour_anchors=True).
    Time budget is SOFT: never abort a mid-trial run without validation. After
    at least one complete trial, stop launching trials if budget has expired.
    Best-so-far can be checkpointed through on_best after every full validation.
    No guarantee of a global optimum or improvement in every individual metric.
    """
    if isinstance(trials,bool) or not isinstance(trials,int) or not 1 <= trials <= 30:
        raise ValueError("trials must be an integer from 1 to 30")
    if isinstance(seed,bool) or not isinstance(seed,int) or not -2**31 <= seed <= 2**31-1:
        raise ValueError("seed must be a 32-bit integer")
    budget=float(time_budget_sec)
    if not math.isfinite(budget) or budget < 0 or budget > 3600:
        raise ValueError("time_budget_sec must be between 0 and 3600")
    if not isinstance(contour_anchors,bool):
        raise ValueError("contour_anchors must be boolean")
    if not isinstance(advanced_geometry,bool):
        raise ValueError("advanced_geometry must be boolean")
    if not isinstance(advanced_search,bool):
        raise ValueError("advanced_search must be boolean")
    from .multiobjective import normalized_weights, metric_vector, frontier
    normalized = normalized_weights(objective_weights)
    if type(guided_objectives) is not bool:
        raise ValueError('guided_objectives must be boolean')
    if guided_objectives and normalized is None:
        raise ValueError('guided_objectives requires objective_weights')
    if type(cut_common_line_audit) is not bool:
        raise ValueError('cut_common_line_audit must be boolean')
    if cut_common_line_audit and kwargs.get('operation', 'engrave') != 'cut':
        raise ValueError('Common-line inspection requires Cutting technology')
    def finish(result, data_ref=data, include_cut_audit=True):
        if normalized is not None:
            result['report']['multiobjective'] = {
                'weights':normalized, 'metrics':metric_vector(result),
                'selection_only':True,
                'construction_guided': (guided_objectives and result.get('settings',{}).get('mode')!='ordered' and kwargs.get('flow','free')=='free'),
                'note':'Weights guide candidate placement and rank completed feasible trials; travel is a centroid proxy, not CAM.'}
            result['settings']['objective_weights']=objective_weights
        if cut_common_line_audit and include_cut_audit:
            from .common_lines import inspect_source_common_edges
            result['report']['common_line_audit']=inspect_source_common_edges(data_ref)
            result['settings']['cut_common_line_audit']=True
        return result
    def run_safe(**call_options):
        try:
            return _layout_once(data, **call_options)
        except ValueError as exc:
            if (call_options.get('family_layout') != 'family_first'
                    or 'Cannot fit family' not in str(exc)):
                raise
            # Family-first is an aesthetic preference, never a reason to lose
            # an otherwise possible, fully validated layout. Make the fallback
            # transparent to the user; NEVER claim the result is family-first.
            alternative=dict(call_options,family_layout='compact')
            result, shapes = _layout_once(data, **alternative)
            result['report']['family_layout']['requested']='family_first'
            result['report']['family_layout']['fallback_reason']=str(exc)
            result['report']['warnings'].append(
                'Family-first shelving could not fit this plate at the requested gap; '
                'verified compact fallback used. Review arrangement before applying.')
            return result, shapes

    if trials == 1:
        result, shapes = run_safe(progress=progress,
                  order_strategy="baseline", random_seed=seed,
                  contour_anchors=contour_anchors, advanced_geometry=advanced_geometry, advanced_search=advanced_search,
                  search_weights=normalized if guided_objectives else None, **kwargs)
        result['report']['search']={'guided_objectives':guided_objectives,'requested_trials':1,'completed_trials':1,
                'best_trial':1,'seed':seed,'time_budget_sec':budget,
                'elapsed_sec':None,'score':round(_solution_score(result,kwargs.get('mode','uniform'),objective_weights),6),
                'contour_anchors':contour_anchors,'advanced_geometry':advanced_geometry,'advanced_search':advanced_search,'trial_summaries':[]}
        finish(result)
        if on_best: on_best(result,shapes)
        return result,shapes
    start=time.monotonic()
    mode=kwargs.get('mode','uniform')
    best=None; best_geometry=None; best_score=math.inf; best_trial=None
    records=[]; failed=[]
    for trial in range(trials):
        if trial and budget and time.monotonic()-start >= budget:
            break
        variant=('baseline','perimeter','max_dimension','shuffled')[trial % 4]
        if trial >= 4: variant='shuffled'
        if mode=='ordered': variant='baseline'
        policy = ('default', 'balanced', 'footprint')[trial % 3] if mode=='ordered' else 'default'
        def nested_progress(stage, done, total):
            if progress:
                weights={'preparing':0,'placing':.05,'refining':.85,'compacting':.95,'validating':.98,'complete':1.0}
                frac=weights.get(stage,0.)
                if stage=='placing': frac=.05+.78*done/max(1,total)
                elif stage=='refining': frac=.85+.09*done/max(1,total)
                elif stage=='compacting': frac=.94+.04*done/max(1,total)
                progress('searching',int(round((trial+frac)*1000)),trials*1000)
        try:
            result, shapes = run_safe(progress=nested_progress,
                    order_strategy=variant,random_seed=seed+trial*17,
                    contour_anchors=contour_anchors, advanced_geometry=advanced_geometry, advanced_search=advanced_search,
                    candidate_policy=policy, search_weights=(
                        # The weighted policy plus 3 pure objective directions
                        # builds diverse geometry rather than only reranking.
                        (normalized if trial % 5 in (0, 4) else
                         {key: float(key == ('area', 'spacing', 'travel')[(trial-1) % 3])
                          for key in ('area','spacing','travel')})
                        if guided_objectives and normalized is not None and mode != 'ordered' and kwargs.get('flow','free') == 'free'
                        else None), **kwargs)
        except ValueError as exc:
            failed.append({'trial':trial+1,'reason':str(exc)})
            if progress: progress('searching',(trial+1)*1000,trials*1000)
            continue
        score=_solution_score(result,mode,objective_weights)
        if on_trial is not None: on_trial(trial+1, result, shapes)
        records.append({'trial':trial+1,'strategy':variant,'score':round(score,7),
                        'bbox_mm2':result['report']['occupied_bbox_mm2'],
                        'nearest_3_stdev_mm':result['report']['nearest_3_stdev_mm'],
                        'metrics':metric_vector(result),
                        'travel_mm':result['report']['travel_proxy']['travel_total_mm'],
                        'construction_goal':('weighted' if trial % 5 in (0,4) else ('area','spacing','travel')[(trial-1)%3])
                           if guided_objectives and normalized is not None and mode!='ordered' and kwargs.get('flow','free')=='free' else 'baseline'})
        if score < best_score-1e-10:
            best,best_geometry,best_score,best_trial=result,shapes,score,trial+1
            if on_best: on_best(finish(best,include_cut_audit=False),best_geometry)
        if progress: progress('searching',(trial+1)*1000,trials*1000)
    if best is None:
        raise ValueError('No feasible trial: '+('; '.join(x['reason'] for x in failed[:3]) or 'unknown error'))
    elapsed=time.monotonic()-start
    best['report']['search']={'guided_objectives':guided_objectives,'requested_trials':trials,
            'completed_trials':len(records),'failed_trials':failed,
            'best_trial':best_trial,'seed':seed,'time_budget_sec':budget,
            'elapsed_sec':round(elapsed,3),'score':round(best_score,6),
            'contour_anchors':contour_anchors,'advanced_geometry':advanced_geometry,'advanced_search':advanced_search,'trial_summaries':records,
            'soft_budget_exceeded':bool(budget and elapsed>budget)}
    finish(best)
    front = frontier(records)
    best['report']['search']['pareto_frontier']=[records[i]['trial'] for i in front]
    best['report']['search']['pareto_solutions']=[records[i] for i in front]
    if progress: progress('complete',1,1)
    return best,best_geometry
