"""Bounded exact polygonal configuration-space obstacles for *exported* artwork.

For sets A and B, the forbidden translation domain is A (+) (-B).
The set is decomposed into convex triangles; their Minkowski sums are convex
hulls of all vertex differences. This is exact for the imported polygonal
surfaces when the triangulation is complete. Clearances are approximated by
polygonal buffering and final placements must be validated on original shapes.

This function never silently claims completeness after approximation or hitting
work limits: it returns None, and the caller may use heuristic candidates.
No CAM or cutter compensation is produced here.
"""
from __future__ import annotations

import math
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union, triangulate
from shapely.geometry.base import BaseGeometry

try:
    from shapely import constrained_delaunay_triangles as _constrained
except ImportError:  # Shapely 2.0: use verified unconstrained triangles
    _constrained = None


def _polygons(g: BaseGeometry):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        out=[]
        for part in g.geoms:
            out.extend(_polygons(part))
        return out
    return []


def _triangles(g: BaseGeometry, *, limit=36):
    """Certified decomposition into triangles, or None on complexity/failure."""
    out=[]
    polygons=_polygons(g)
    if not polygons or sum(p.area for p in polygons) <= 1e-9:
        return None
    for poly in polygons:
        if (not poly.is_valid or poly.area < 1e-10 or
                len(poly.exterior.coords)+sum(len(r.coords) for r in poly.interiors)>180):
            return None
        if _constrained is not None:
            cells=list(_constrained(poly).geoms)
        else:
            cells=[tri for tri in triangulate(poly) if poly.covers(tri)]
        for tri in cells:
            if tri.area < 1e-12:
                continue
            if not poly.covers(tri):
                return None
            if len(tri.exterior.coords) != 4:
                return None
            out.append(tri)
            if len(out)>limit:
                return None
        # Completeness is essential. Covers all occupied surface but not holes.
        area=sum(x.area for x in cells)
        if abs(poly.area - area) > max(1e-6, poly.area*1e-7):
            return None
    return out


def general_no_fit_polygon(fixed: BaseGeometry, moving: BaseGeometry, clearance=0.,
                           *, max_triangles=36, max_pairs=500):
    """Concave/MultiPolygon/holes NFP for bounded polygon complexity.

    Returns None when unable to certify the entire construction, rather than a
    potentially incomplete forbidden zone. The moving object's reference is
    the source-coordinate origin (not its centroid).
    """
    if not math.isfinite(clearance) or clearance<0:
        raise ValueError('clearance must be finite and nonnegative')
    if max_triangles<1 or max_pairs<1:
        raise ValueError('complexity limits must be positive')
    left=_triangles(fixed,limit=max_triangles)
    right=_triangles(moving,limit=max_triangles)
    if left is None or right is None or len(left)*len(right)>max_pairs:
        return None
    terms=[]
    for a in left:
        aa=list(a.exterior.coords)[:-1]
        for b in right:
            bb=list(b.exterior.coords)[:-1]
            terms.append(MultiPoint([(x-u,y-v) for x,y in aa for u,v in bb]).convex_hull)
    union=unary_union(terms)
    if not union.is_valid:
        union=union.buffer(0)
    if clearance:
        union=union.buffer(clearance,quad_segs=12)
    return union if not union.is_empty else None


def nfp_boundary_candidates(fixed, moving, gap, *, max_samples=22,
                            complexity=36, max_pairs=500):
    """Boundary candidates (not automatically legal); status reports exactness.

    A small outward epsilon avoids roundoff on just-touching boundaries; every
    candidate still requires original-distance validation with the real gap.
    """
    obstacle=general_no_fit_polygon(fixed,moving,gap,max_triangles=complexity,
                                    max_pairs=max_pairs)
    if obstacle is None:
        return [],False
    points=[]
    for part in _polygons(obstacle):
        rings=[part.exterior, *part.interiors]
        for ring in rings:
            length=ring.length
            if length<=0: continue
            count=min(max_samples,max(4,int(length / max(.3,gap/2))))
            # Include extrema, plus arclength-uniform samples. Do not infer
            # outward normal for hole boundaries; final validation decides.
            coords=list(ring.coords)
            anchors=[(x,y) for x,y in coords]
            anchors.extend(tuple(ring.interpolate(i*length/count).coords[0])
                           for i in range(count))
            if len(anchors)>max_samples:
                anchors=[anchors[round(i*(len(anchors)-1)/(max_samples-1))]
                         for i in range(max_samples)]
            cx,cy=part.centroid.x,part.centroid.y
            for x,y in anchors:
                dx,dy=x-cx,y-cy
                norm=math.hypot(dx,dy) or 1.
                points.append((x+dx/norm*.002,y+dy/norm*.002))
    return list(dict.fromkeys((round(x,5),round(y,5)) for x,y in points)),True
