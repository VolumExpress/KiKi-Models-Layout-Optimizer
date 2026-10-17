"""Optional family clustering; does not alter or merge original artwork."""
from __future__ import annotations
from collections import defaultdict
from shapely.affinity import translate
from shapely.ops import unary_union
from shapely.geometry import Polygon
from .family_layout import ink_coverage
from .geometry import manual_family, normalized_signature, signature_similarity


def normalized_outer_signature(shape):
    """Stroke-thickness insensitive outline proxy. Only used for opt-in auto matching."""
    parts=list(shape.geoms) if hasattr(shape, 'geoms') else [shape]
    if not parts or any(not isinstance(part,Polygon) for part in parts):
        return None
    outside=unary_union([Polygon(part.exterior) for part in parts])
    return normalized_signature(outside)


def outline_topology(shape):
    parts=list(shape.geoms) if hasattr(shape, 'geoms') else [shape]
    if any(not isinstance(p,Polygon) for p in parts):
        return None
    return len(parts),sum(len(p.interiors) for p in parts)


def detect_families(objects, shapes, mode="off", threshold=0.97, outline_aware=False):
    if mode == "off":
        return {str(o["id"]): str(o["id"]) for o in objects}, []
    if mode not in ("auto", "named"):
        raise ValueError("Family mode must be off, named or auto")
    ids = [str(ob["id"]) for ob in objects]
    parent = {i: i for i in ids}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def join(a, b):
        pa, pb = find(a), find(b)
        if pa != pb:
            parent[pb] = pa

    byname = defaultdict(list)
    for ob in objects:
        key = manual_family(ob)
        if key:
            byname[key].append(str(ob["id"]))
    for group in byname.values():
        for other in group[1:]:
            join(group[0], other)

    if mode == "auto":
        # v0.6.4: all signatures are normalized to the origin (see geometry.py).
        # Complete-link assignment avoids chaining A~B~C when A and C differ.
        # Never auto-join two DIFFERENT explicitly named symbol families.
        fingerprints = {oid: normalized_signature(shapes[oid]) for oid in ids}
        by_id = {str(ob["id"]): ob for ob in objects}
        outlines={}
        if outline_aware:
            outlines={oid: normalized_outer_signature(shapes[oid])
                      for oid in ids if ink_coverage(shapes[oid]) < .32}
        topology={oid: outline_topology(shapes[oid]) for oid in outlines}
        def compatible(a, b):
            ka, kb = manual_family(by_id[a]), manual_family(by_id[b])
            if ka and kb and ka != kb:
                return False
            if signature_similarity(fingerprints[a], fingerprints[b]) >= threshold:
                return True
            if outline_aware and a in outlines and b in outlines:
                # Outer-shell matching is a candidate only for genuinely thin
                # outlined objects with identical component/hole topology.
                # Never merge cross-named symbol codes. Exterior silhouettes
                # of different internal motifs can still coincide: REVIEW.
                return (outlines[a] is not None and outlines[b] is not None
                    and topology[a] == topology[b]
                    and signature_similarity(outlines[a],outlines[b]) >= .975)
            return False
        # Start from manual clusters; preserve named members as known ground truth.
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if find(a) == find(b):
                    continue
                members_a = [v for v in ids if find(v) == find(a)]
                members_b = [v for v in ids if find(v) == find(b)]
                if all(compatible(x, y) for x in members_a for y in members_b):
                    join(a, b)
    labels = {oid: find(oid) for oid in ids}
    groups = defaultdict(list)
    for oid, label in labels.items():
        groups[label].append(oid)
    warnings = ["Auto family detection is tentative; visually confirm merged silhouettes and naming."] if mode == "auto" else []
    if outline_aware and mode == "auto":
        warnings.append("Outline-aware matching ignores stroke weight. Inspect suggested families for false positives before fabrication.")
    return labels, warnings


def build_units(objects, shapes, labels, gap, max_group_width):
    """Pack same-emblem sizes into a compact rectangular *logical* unit.

    Returns geometry and per-item offsets, with local geometry centered at 0,0.
    """
    members = defaultdict(list)
    for ob in objects:
        oid = str(ob["id"])
        members[labels[oid]].append(oid)
    result = []
    for family, ids in members.items():
        ids = sorted(ids, key=lambda oid: shapes[oid].area)  # small to large
        if len(ids) == 1:
            result.append({"family": family, "ids": ids, "geometry": shapes[ids[0]],
                           "offsets": {ids[0]: (0.0, 0.0)}})
            continue
        heights = [shapes[oid].bounds[3] - shapes[oid].bounds[1] for oid in ids]
        max_h = max(heights)
        x, row_y, row_h = 0.0, 0.0, 0.0
        translated = []
        positions = {}
        for oid in ids:
            geom = shapes[oid]
            x0, y0, x1, y1 = geom.bounds
            width, height = x1 - x0, y1 - y0
            if x and x + width > max_group_width:
                x, row_y, row_h = 0.0, row_y + max(row_h, max_h if row_y == 0 else 0.0) + gap, 0.0
            dx = x - x0
            dy = row_y - y0 + (max_h - height) / 2 if row_y == 0 else row_y - y0
            translated.append(translate(geom, dx, dy))
            positions[oid] = (dx, dy)
            x += width + gap
            row_h = max(row_h, height)
        unit_shape = unary_union(translated)
        minx, miny, maxx, maxy = unit_shape.bounds
        centre = ((minx + maxx)/2, (miny + maxy)/2)
        unit_shape = translate(unit_shape, -centre[0], -centre[1])
        offsets = {oid: (p[0]-centre[0], p[1]-centre[1]) for oid, p in positions.items()}
        result.append({"family": family, "ids": ids, "geometry": unit_shape,
                       "offsets": offsets})
    return result
