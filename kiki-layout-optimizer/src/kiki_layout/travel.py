"""Visual-only planning proxy for laser-off jumps between marking islands.

The actual galvo marking application decides contour, hatch, lead-in/out, order,
scan settings, speed and lens distortions. Nothing here is a machine toolpath.
"""
from __future__ import annotations
import csv
import io
import math
from statistics import median
from xml.sax.saxutils import escape


def _distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def _path_length(indices, points, start):
    last=start
    total=0.0
    for i in indices:
        total+=_distance(last,points[i]);last=points[i]
    return total


def _two_opt(route, points, start):
    # Fixed path start, no closed return to zero; best-improvement limited rounds.
    if len(route)>300:
        return route
    for _ in range(3):
        improvement=False
        for i in range(len(route)-1):
            before=start if i==0 else points[route[i-1]]
            ai=points[route[i]]
            for j in range(i+1,len(route)):
                bj=points[route[j]]
                after=points[route[j+1]] if j+1<len(route) else None
                old=_distance(before,ai)+(_distance(bj,after) if after is not None else 0)
                new=_distance(before,bj)+(_distance(ai,after) if after is not None else 0)
                if new < old-1e-8:
                    route[i:j+1]=reversed(route[i:j+1]);improvement=True
                    break
            if improvement:break
        if not improvement:break
    return route


def plan_travel(geometries, *, source_order=None, order="nearest",
                start=(0.0,0.0), long_jump_mm=15.0):
    if order not in ("source","nearest","rows","columns"):
        raise ValueError("Unsupported laser travel proxy order")
    if not math.isfinite(long_jump_mm) or long_jump_mm<=0:
        raise ValueError("long_jump_mm must be positive and finite")
    keys=list(geometries)
    if not keys:
        return {"method":order,"steps":[],"summary":{
            "travel_total_mm":0.0,"long_jump_count":0,"longest_jump_mm":0.0}}
    coords={k:tuple(map(float,geometries[k].centroid.coords[0])) for k in keys}
    if order=="source":
        ordered=[k for k in (source_order or keys) if k in coords]
        if set(ordered)!=set(keys):ordered+=sorted(set(keys)-set(ordered))
    elif order=="nearest":
        remaining=set(keys);ordered=[];current=start
        while remaining:
            pick=min(remaining,key=lambda k:(_distance(current,coords[k]),k))
            ordered.append(pick);remaining.remove(pick);current=coords[pick]
        ordered=_two_opt(ordered,coords,start)
    else:
        bounds=[g.bounds for g in geometries.values()]
        horizontal=order=="rows"
        sizes=([b[3]-b[1] for b in bounds] if horizontal
               else [b[2]-b[0] for b in bounds])
        pitch=max(0.1,median(sizes))
        # Deterministic sweep bands, serpentine traversal within each band.
        primary=1 if horizontal else 0
        secondary=0 if horizontal else 1
        baseline=min(coords[k][primary] for k in keys)
        bands={}
        for k in keys:
            band=int((coords[k][primary]-baseline)/pitch)
            bands.setdefault(band,[]).append(k)
        ordered=[]
        for row,band in enumerate(sorted(bands)):
            ordered+=sorted(bands[band],key=lambda k:(coords[k][secondary],k),
                            reverse=(row%2==1))
    current=start;steps=[];total=0.;long_count=0;longest=0.
    for index,k in enumerate(ordered,1):
        target=coords[k];distance=_distance(current,target)
        steps.append({"number":index,"id":k,"from_x_mm":round(current[0],5),
                      "from_y_mm":round(current[1],5),
                      "to_x_mm":round(target[0],5),"to_y_mm":round(target[1],5),
                      "jump_mm":round(distance,5)})
        total+=distance;longest=max(longest,distance)
        if distance>long_jump_mm:long_count+=1
        current=target
    return {"method":order,"start_mm":list(start),"steps":steps,
            "summary":{"travel_total_mm":round(total,4),
                       "longest_jump_mm":round(longest,4),
                       "long_jump_count":long_count,
                       "long_jump_threshold_mm":long_jump_mm,
                       "note":"Centroid-to-centroid laser-off travel PROXY; not a laser path or runtime."}}


def travel_csv(laser_plan):
    buf=io.StringIO(newline="")
    w=csv.DictWriter(buf,fieldnames=["number","id","from_x_mm","from_y_mm",
                                      "to_x_mm","to_y_mm","jump_mm"])
    w.writeheader();w.writerows(laser_plan["steps"])
    return buf.getvalue()


def travel_preview_svg(geometries, result):
    w=result["artboard"]["width_mm"];h=result["artboard"]["height_mm"]
    edges=result["settings"]["margins_mm"]
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">',
           f'<rect width="{w}" height="{h}" fill="white" stroke="#333" stroke-width="0.25"/>',
           f'<rect x="{edges["left"]}" y="{edges["top"]}" width="{w-edges["left"]-edges["right"]}" height="{h-edges["top"]-edges["bottom"]}" fill="none" stroke="#c33" stroke-dasharray="1 1" stroke-width="0.3"/>']
    for oid,g in geometries.items():
        b=g.bounds
        lines.append(f'<rect x="{b[0]:.3f}" y="{b[1]:.3f}" width="{b[2]-b[0]:.3f}" height="{b[3]-b[1]:.3f}" fill="#dceaf4" stroke="#769bb4" stroke-width="0.18"><title>{escape(oid)}</title></rect>')
    for step in result["laser_plan"]["steps"]:
        x1=step["from_x_mm"];y1=step["from_y_mm"];x2=step["to_x_mm"];y2=step["to_y_mm"]
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ff6b35" stroke-width="0.22" stroke-dasharray="0.7 0.7"/>')
        lines.append(f'<circle cx="{x2}" cy="{y2}" r="0.75" fill="#15457a"/>')
        lines.append(f'<text x="{x2+0.9}" y="{y2-0.9}" font-size="2.4" fill="#111">{step["number"]}</text>')
    lines.append('</svg>')
    return '\n'.join(lines)
