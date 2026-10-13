"""v0.7 multi-objective selection across independently validated full layouts.

Metrics are dimensionless and use fixed scales per input sheet, not per-trial
normalization.  Therefore the weights/score remain stable as new trials appear.
This module does not claim a globally optimal packing or a real laser timeline.
"""
from __future__ import annotations
import math

NAMES = ('area', 'spacing', 'travel')


def normalized_weights(weights):
    if weights is None:
        return None
    if not isinstance(weights, dict) or set(weights) != set(NAMES):
        raise ValueError('objective_weights requires area, spacing, travel')
    values = {}
    for key in NAMES:
        value = weights[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'Invalid weight for {key}')
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 10:
            raise ValueError(f'Weight for {key} must be finite, between 0 and 10')
        values[key] = value
    total = sum(values.values())
    if not total:
        raise ValueError('At least one objective weight must be positive')
    return {k: values[k]/total for k in NAMES}


def metric_vector(result):
    report = result['report']
    plate = max(float(report['plate_area_mm2']), 1e-9)
    count = max(1, int(report['object_count']))
    sheet = result['artboard']
    diag = max(1e-9, math.hypot(sheet['width_mm'], sheet['height_mm']))
    gap = max(.5, float(result['settings']['gap_mm']))
    stdev = float(report.get('nearest_3_stdev_mm') or 0.0)
    excess = max(0., float(report.get('nearest_3_mean_mm') or gap) - gap)
    # Separation objective rewards consistent, *tight* nearest-neighbour gaps.
    spacing = (0.75*stdev + 0.25*excess)/gap
    route = float(report.get('travel_proxy',{}).get('travel_total_mm',0.0))
    return {
        'area': float(report['occupied_bbox_mm2'])/plate,
        'spacing': spacing,
        # Dimensionless proxy; scales with number of visited objects and sheet size.
        'travel': route/(diag*math.sqrt(count)),
    }


def weighted_score(result, weights):
    norm = normalized_weights(weights)
    metrics = metric_vector(result)
    return sum(norm[k]*metrics[k] for k in NAMES)


def frontier(records):
    """Indices of non-dominated, distinct solutions, minimizing all 3 metrics."""
    keep = []
    for i, a in enumerate(records):
        va = a['metrics']
        dominated = False
        for j, b in enumerate(records):
            if i == j: continue
            vb = b['metrics']
            if (all(vb[k] <= va[k]+1e-10 for k in NAMES) and
                (any(vb[k] < va[k]-1e-10 for k in NAMES) or
                 (j < i and all(abs(vb[k]-va[k]) <= 1e-10 for k in NAMES)))):
                dominated = True
                break
        if not dominated: keep.append(i)
    return keep



def construction_score(candidate, placed, gap, board_width, board_height, footprint, origin, weights):
    """Cheap dimensionless ranking of FEASIBLE contour positions.

    This function never accepts/rejects geometry: _layout_once validates with
    exact Shapely contours.  Bounding-box proximity is a heuristic only.
    """
    import math
    w=normalized_weights(weights)
    if not placed:
        return (w['area']*footprint/max(board_width*board_height,1e-9)
                + 0.000001*(candidate.bounds[0]+candidate.bounds[1]))
    bb=candidate.bounds
    proxy=[]
    for ob in placed:
        a=ob.bounds
        dx=max(0.,a[0]-bb[2],bb[0]-a[2]); dy=max(0.,a[1]-bb[3],bb[1]-a[3])
        proxy.append(math.hypot(dx,dy))
    proxy.sort()
    nn=proxy[:3]
    # Desire near minimum safe separation, not arbitrarily distant islands.
    spacing=sum(min(4.,abs(d-gap)/max(gap,.5))**2 for d in nn)/len(nn)
    last=placed[-1].bounds
    xc=(bb[0]+bb[2])/2; yc=(bb[1]+bb[3])/2
    lc=(last[0]+last[2])/2; ly=(last[1]+last[3])/2
    travel=math.hypot(xc-lc,yc-ly)/max(1e-9,math.hypot(board_width,board_height))
    area=footprint/max(board_width*board_height,1e-9)
    anchor=0.000001*((xc-origin[0])/max(board_width,1)+(yc-origin[1])/max(board_height,1))
    return (w['area']*area + .12*w['spacing']*spacing + .45*w['travel']*travel + anchor)
