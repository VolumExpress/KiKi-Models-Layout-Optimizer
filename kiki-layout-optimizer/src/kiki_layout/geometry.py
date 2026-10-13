"""Interpret Illustrator-exported local-coordinate contours in millimetres.

Important: polyline sampling has finite tolerance; final production audit in Illustrator
is mandatory. This module deliberately rejects unsupported geometry types.
"""
from __future__ import annotations

from shapely.affinity import scale, translate
from shapely.geometry import GeometryCollection, Polygon, LineString
from shapely.ops import unary_union
from shapely import contains_xy
import math
import re

SIZE_RE = re.compile(r"(?<!\d)(?:3|5[.,]5|7|9|11|13)\s*(?:mm|мм)(?!\w)", re.I)
# P10-SLOT-...__P10-SYM-007__11.0mm__copy... names identify a motif
# independent of its slot, size and copy index.
SYM_RE = re.compile(r"(P\d{2}-SYM-\d{3})(?!\d)", re.I)


def as_polygon(points):
    if len(points) < 3:
        raise ValueError("Closed path must contain at least 3 points")
    poly = Polygon(points)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.area < 1e-7:
        raise ValueError("Empty or degenerate closed contour")
    return poly


def from_tree(node):
    kind = node.get("type")
    if kind == "path":
        return as_polygon(node["ring"])
    if kind == "stroke":
        # Buffer Illustrator stroke centreline by half the line thickness.
        # Curve flattening / caps / joins make this an approximation of the
        # visual paint envelope, not a CAM laser marking path.
        points = node["points"]
        if len(points) < 2:
            raise ValueError("Stroke path needs at least two points")
        width = float(node["width_mm"])
        if not math.isfinite(width) or width <= 0:
            raise ValueError("Stroke width must be positive and finite")
        if node.get("closed", False):
            points = list(points) + [points[0]]
        cap = node.get("cap", "flat")
        join = node.get("join", "mitre")
        if cap not in ("flat", "round", "square"):
            raise ValueError("Unrecognized stroke cap")
        if join not in ("mitre", "round", "bevel"):
            raise ValueError("Unrecognized stroke join")
        limit = float(node.get("mitre_limit", 5))
        if not math.isfinite(limit) or limit < 1.0:
            raise ValueError("Stroke mitre_limit must be finite and >= 1")
        geom = LineString(points).buffer(width / 2.0, cap_style=cap,
                                         join_style=join, mitre_limit=limit,
                                         quad_segs=16)
        if geom.is_empty:
            raise ValueError("Empty stroke envelope")
        return geom
    if kind == "compound":
        # Even/odd interpretation; nonzero-winding and complicated self-intersections
        # require a future fill-rule-aware implementation.
        geom = GeometryCollection()
        for ring in node.get("rings", []):
            geom = geom.symmetric_difference(as_polygon(ring))
        return geom
    if kind == "group":
        parts = [from_tree(ch) for ch in node.get("children", [])]
        return unary_union(parts) if parts else GeometryCollection()
    raise ValueError(f"Unsupported geometry type: {kind}")


def get_shapes(data):
    objects = data.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("Input must contain a nonempty objects list")
    found = {}
    for ob in objects:
        oid = str(ob["id"])
        if oid in found:
            raise ValueError(f"Duplicate object ID: {oid}")
        geom = from_tree(ob["geometry"])
        if geom.is_empty or geom.area < 1e-6:
            raise ValueError(f"Empty geometry for object {oid}")
        found[oid] = geom
    return found


def normalized_signature(shape, n=28):
    """Fixed-scale shape fingerprint for same silhouette at different physical sizes.

    Scale and translation invariant, NOT rotation or reflection invariant.
    It is intentionally strict to limit erroneous automatic family matches.
    """
    minx, miny, maxx, maxy = shape.bounds
    w, h = maxx - minx, maxy - miny
    if w < 1e-7 or h < 1e-7:
        raise ValueError("Degenerate geometry")
    normalized = scale(translate(shape, -minx, -miny), xfact=1.0 / w, yfact=1.0 / h, origin=(0, 0))
    xs = [(i + 0.5) / n for i in range(n)]
    ys = [(j + 0.5) / n for j in range(n)]
    signature = tuple(bool(contains_xy(normalized, x, y)) for y in ys for x in xs)
    return w / h, signature


def signature_similarity(left, right):
    ar_a, a = left
    ar_b, b = right
    if abs(math.log(ar_a / ar_b)) > 0.022:
        return 0.0
    intersection = sum(x and y for x, y in zip(a, b))
    union = sum(x or y for x, y in zip(a, b))
    return intersection / union if union else 0.0


def manual_family(ob):
    if ob.get("family"):
        return "manual:" + str(ob["family"]).strip().casefold()
    # Naming convention, e.g. "Ultramarines__5.5mm" or "Ultra | 7mm".
    # Unlabelled items are matched by silhouette only.
    name = str(ob.get("name", ""))
    symbol = SYM_RE.search(name)
    if symbol:
        return "sym:" + symbol.group(1).casefold()
    if SIZE_RE.search(name):
        cleaned = SIZE_RE.sub("", name)
        cleaned = re.sub(r"[_|\- ]+$", "", cleaned).strip().casefold()
        if len(cleaned) > 2:
            return "name:" + cleaned
    return None
