"""Bounded rectangle packing rescue for intact family blocks.

Used only if the ordered shelf constructor fails. Padded bounding boxes are
conservative: accepted placements meet the same exact Shapely contour checks.
No original geometry or physical emblem sizes are modified.
"""
from __future__ import annotations
import random
from shapely.affinity import translate

_EPS = 1e-7


def _remove_contained(rectangles):
    result = []
    for i, a in enumerate(rectangles):
        x, y, w, h = a
        if not any(i != j and b[0] <= x + _EPS and b[1] <= y + _EPS
                   and b[0] + b[2] >= x + w - _EPS
                   and b[1] + b[3] >= y + h - _EPS
                   for j, b in enumerate(rectangles)):
            result.append(a)
    return result


def _allocate(ordered, usable_width, usable_height, gap, policy):
    # A padded box may extend past the plate by its padding only. The actual
    # symbol never extends past the requested plate margins.
    free = [(0., 0., usable_width + gap, usable_height + gap)]
    allocated = {}
    for index, w0, h0 in ordered:
        w, h = w0 + gap, h0 + gap
        candidates = []
        for fx, fy, fw, fh in free:
            if fw + _EPS < w or fh + _EPS < h:
                continue
            if policy == 'short':
                score = (min(fw - w, fh - h), max(fw - w, fh - h), fy, fx)
            elif policy == 'area':
                score = (fw * fh - w * h, min(fw - w, fh - h), fy, fx)
            elif policy == 'bottom':
                score = (fy + h, fx)
            else:
                score = (max(fw - w, fh - h), min(fw - w, fh - h), fy, fx)
            candidates.append((score, (fx, fy, w, h)))
        if not candidates:
            return None
        x, y, w, h = min(candidates, key=lambda value: value[0])[1]
        allocated[index] = (x, y)
        new_free = []
        for a, b, c, d in free:
            if x >= a + c - _EPS or x + w <= a + _EPS or y >= b + d - _EPS or y + h <= b + _EPS:
                new_free.append((a, b, c, d))
                continue
            if x > a + _EPS:
                new_free.append((a, b, x - a, d))
            if x + w < a + c - _EPS:
                new_free.append((x + w, b, a + c - x - w, d))
            if y > b + _EPS:
                new_free.append((a, b, c, y - b))
            if y + h < b + d - _EPS:
                new_free.append((a, y + h, c, b + d - y - h))
        free = _remove_contained(new_free)
    return allocated


def pack_family_units(units, width, height, margins, gap, *, seed=42, per_policy=72):
    """Return [(geometry, dx, dy, 0), ...] in original unit order or None.

    No rotations or locked objects are supported by this rescue path. The
    caller must check those constraints and retain the existing solver as the
    general fallback.
    """
    left, top, right, bottom = margins
    usable_w, usable_h = width - left - right, height - top - bottom
    if usable_w <= 0 or usable_h <= 0:
        return None
    if not units:
        return []
    specs = []
    for index, unit in enumerate(units):
        xmin, ymin, xmax, ymax = unit['geometry'].bounds
        w, h = xmax - xmin, ymax - ymin
        if w > usable_w + _EPS or h > usable_h + _EPS:
            return None
        specs.append((index, w, h, unit.get('visual_style', 'mixed')))
    rng = random.Random(seed)
    styles = ('solid', 'mixed', 'outline')
    for policy in ('short', 'area', 'bottom', 'long'):
        for trial in range(per_policy):
            ordered = []
            for style in styles:
                group = [(i, w, h) for i, w, h, category in specs if category == style]
                if trial == 0:
                    group.sort(key=lambda item: -item[1] * item[2])
                elif trial == 1:
                    group.sort(key=lambda item: -max(item[1], item[2]))
                elif trial == 2:
                    group.sort(key=lambda item: -item[1])
                elif trial == 3:
                    group.sort(key=lambda item: -item[2])
                elif trial == 4:
                    group.sort(key=lambda item: -(item[1] + item[2]))
                else:
                    rng.shuffle(group)
                ordered.extend(group)
            ordered.extend((i, w, h) for i, w, h, style in specs if style not in styles)
            assigned = _allocate(ordered, usable_w, usable_h, gap, policy)
            if assigned is None:
                continue
            placement = []
            for i, unit in enumerate(units):
                x, y = assigned[i]
                x0, y0, _, _ = unit['geometry'].bounds
                dx, dy = left + x - x0, top + y - y0
                placement.append((translate(unit['geometry'], dx, dy), dx, dy, 0))
            # Final contour-level validation remains authoritative.
            from .engine import contained, collision_free
            taken = []
            for geometry, _, _, _ in placement:
                if not contained(geometry, width, height, margins) or not collision_free(geometry, taken, gap):
                    break
                taken.append(geometry)
            else:
                return placement
    return None
