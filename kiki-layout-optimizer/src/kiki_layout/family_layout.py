"""Family-first shelf placement helpers (v0.7.2).

These helpers NEVER rewrite individual contours. Each logical family is placed as
one rigid geometry, preserving the source shape and the size series in that family.
Rows prioritize visual navigation, not global minimum bounding-box area.
"""
from __future__ import annotations

from shapely.affinity import translate

EPS = 1e-5


def ink_coverage(shape):
    a, b, c, d = shape.bounds
    return shape.area / max((c-a) * (d-b), 1e-9)


def visual_style(unit, shapes):
    """Conservative proxy, not a ground-truth Illustrator stroke/fill attribute.

    The exporter currently approximates outlined paths with closed polygons.
    Thin/outlined geometry usually covers less of its axis-aligned envelope.
    An intermediate density is classified as mixed (rather than inventing a
    strong claim about its original Illustrator appearance).
    """
    coverages = sorted(ink_coverage(shapes[oid]) for oid in unit['ids'])
    mid = coverages[len(coverages)//2]
    if mid < .29:
        return 'outline'
    if mid > .56:
        return 'solid'
    return 'mixed'


def sort_family_units(units, shapes, strategy='baseline', seed=42):
    """Visible sections: solid, mixed, outlined; keep each family together."""
    import random
    rng = random.Random(seed)
    categories = {'solid':0, 'mixed':1, 'outline':2}
    for unit in units:
        unit['visual_style'] = visual_style(unit, shapes)
    def unit_key(unit):
        a,b,c,d = unit['geometry'].bounds
        w,h=c-a,d-b
        if strategy=='perimeter':
            size_key = -max(w,h)
        elif strategy=='max_dimension':
            size_key = -h
        elif strategy=='shuffled':
            size_key = rng.random()
        else:
            size_key = -len(unit['ids'])
        return (categories[unit['visual_style']],size_key,-len(unit['ids']),-unit['geometry'].area,str(unit['family']))
    return sorted(units, key=unit_key)


def next_shelf_candidate(rotated, obstacles, width, height, margins, gap, cursor,
                         collision_free, contained, max_rows=40):
    """Find a left-to-right shelf slot; preserve exact final Shapely checks.

    May return None if shelves cannot accommodate geometry. The engine then
    uses the validated irregular placement fallback, never silently dropping
    an object or violating a fixation/clearance.
    """
    l,t,r,b=margins
    x0,y0,x1,y1=rotated.bounds
    w,h=x1-x0,y1-y0
    cx,cy,row_h=cursor
    for _ in range(max_rows):
        if cy + h > height-b+EPS:
            return None
        if cx+w > width-r+EPS:
            cy += max(row_h,h) + gap
            cx, row_h = l, 0.0
            continue
        candidate=translate(rotated,cx-x0,cy-y0)
        if contained(candidate,width,height,margins) and collision_free(candidate,obstacles,gap):
            return (candidate,cx-x0,cy-y0,(cx+w+gap,cy,max(row_h,h)))
        # Jump over only actual intersecting/too-close contours. Proximity is
        # checked on native Shapely geometry, not on a simplified silhouette.
        conflicting=[]
        for other in obstacles:
            ax,ay,bx,by=other.bounds
            if bx+gap < cx or ax-gap > cx+w or by+gap < cy or ay-gap > cy+h:
                continue
            if candidate.distance(other)<gap-EPS:
                conflicting.append(bx)
        if conflicting:
            new_x=max(cx+max(gap,.02),max(conflicting)+gap)
            cx=new_x
        else:
            # Degenerate floating precision/boundary case; start a new row.
            cy+=max(row_h,h)+gap
            cx,row_h=l,0.
    return None
