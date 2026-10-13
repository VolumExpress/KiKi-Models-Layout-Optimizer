"""Inspection-only common-line audit for an ORIGINAL Illustrator selection.

This finds coincident polygon boundaries, not toolpaths.  It never modifies
artwork, creates G-code, compensates kerf, or authorizes shared-line cutting.
"""
from __future__ import annotations
from shapely.affinity import translate
from shapely.ops import snap
from .constraints import source_centre_mm
from .geometry import get_shapes


def inspect_source_common_edges(data, *, min_length_mm=0.5, max_candidates=250):
    shapes = get_shapes(data)
    objs = data['objects']
    originals = []
    for ob in objs:
        oid = str(ob['id'])
        x, y = source_centre_mm(ob, data)
        geom = translate(shapes[oid], xoff=x, yoff=y)
        originals.append((oid, geom))
    # Strictly screen by bounding boxes before potentially expensive GEOS work.
    candidates = []
    checked = 0
    skipped = 0
    truncated = False
    for i, (aid, a) in enumerate(originals):
        ax0,ay0,ax1,ay1 = a.bounds
        for bid, b in originals[i+1:]:
            bx0,by0,bx1,by1 = b.bounds
            if min(ax1,bx1) < max(ax0,bx0)-1e-6 or min(ay1,by1) < max(ay0,by0)-1e-6:
                continue
            # Low-complexity cap: non-polygonal or huge outlines require CAM review.
            if len(a.wkb)+len(b.wkb) > 250000:
                continue
            if checked >= 400:
                truncated = True
                break
            checked += 1
            try:
                common = a.boundary.intersection(snap(b.boundary, a.boundary, 0.0001))
                length = float(common.length)
            except Exception:
                # Unsupported/invalid source polygons must not block an otherwise
                # valid CUT layout. Flag incomplete audit for manual inspection.
                skipped += 1
                continue
            if length >= min_length_mm:
                candidates.append({'object_a':aid,'object_b':bid,'coincident_length_mm':round(length,5)})
                if len(candidates) >= max_candidates: break
        if len(candidates) >= max_candidates or truncated: break
    return {
        'status':'INSPECTION_ONLY_NOT_CAM',
        'source':'original_selection_before_packing',
        'candidate_count':len(candidates),
        'pairs_checked':checked,
        'pairs_skipped':skipped,
        'incomplete':truncated or skipped > 0 or len(candidates)>=max_candidates,
        'candidates':candidates,
        'minimum_shared_length_mm':min_length_mm,
        'warnings':[
            'Matches are polygon-envelope boundaries, not verified tool-centre paths.',
            'Kerf compensation, contour direction, lead-in, tabs and inside-before-outside are NOT calculated.',
            'The cut packer enforces a positive material web and does NOT merge common cuts.',
            'Review in CAD/CAM before any cutting. No machine-ready paths are generated.'
        ]
    }
