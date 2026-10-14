"""Experimental shared-boundary VECTOR PREVIEW for already touching cut parts.

This intentionally does not generate CAM, kerf offsets, G-code, lead-ins,
cut sequencing or tabs. It DOES NOT modify or overlap packed objects.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape
from shapely.ops import unary_union
from shapely.affinity import translate
from .geometry import get_shapes
from .constraints import source_centre_mm


def _segments(geom):
    if geom.is_empty: return []
    if hasattr(geom, 'geoms'):
        return [point for g in geom.geoms for point in _segments(g)]
    if geom.geom_type == 'LineString':
        return [list(geom.coords)]
    return []


def analyze_shared_boundaries(shapes, *, min_common_mm=0.5, max_objects=150):
    """Find verifiably shared boundaries of nonoverlapping source polygons.

    Source locations only, *not* candidate nesting positions. The topological
    union noding removes duplicated lines from the preview (once not twice).
    """
    if len(shapes)>max_objects:
        raise ValueError('Too many objects for safe vector draft; use CAM')
    ids=list(shapes)
    for oid,shape in shapes.items():
        if not shape.is_valid or shape.geom_type not in ('Polygon','MultiPolygon'):
            raise ValueError(f'Unsupported or invalid polygon: {oid}')
    common=[]
    for i,aid in enumerate(ids):
        a=shapes[aid]
        for bid in ids[i+1:]:
            b=shapes[bid]
            if a.intersection(b).area>1e-6:
                raise ValueError(f'Parts overlap: {aid}/{bid} (not eligible for shared-line draft)')
            shared=a.boundary.intersection(b.boundary)
            if shared.length>=min_common_mm:
                common.append({'a':aid,'b':bid,'mm':round(shared.length,6)})
    # unary_union nodes and deduplicates coincident LINEWORK. It is a preview
    # geometry, NOT a compensated tool-centre path.
    network=unary_union([geom.boundary for geom in shapes.values()])
    segments=_segments(network)
    return {'status':'DRAFT_NOT_CAM','shared_edges':common,
            'shared_total_mm':round(sum(x['mm'] for x in common),6),
            'unique_vector_length_mm':round(network.length,6),
            'segment_count':len(segments),'segments':segments,
            'warnings':['Original artwork coordinates only; optimized CUT layouts enforce positive material webs.',
                        'Shared boundaries are not kerf compensated; confirm topology, path direction, lead-ins, tabs and cutting order in CAM.',
                        'Do not send this SVG directly to a cutting machine.']}


def source_shapes(data):
    raw=get_shapes(data)
    return {str(o['id']):translate(raw[str(o['id'])],*source_centre_mm(o,data)) for o in data['objects']}


def write_preview(report, path, *, width=145, height=95):
    width=float(width); height=float(height)
    def f(x): return f'{float(x):.5f}'
    path_data=[]
    for line in report['segments']:
        if len(line)>=2:
            path_data.append('M '+' L '.join(f(x)+' '+f(y) for x,y in line))
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(width)}mm" height="{f(height)}mm" '
         f'viewBox="0 0 {f(width)} {f(height)}">'
         '<title>Shared-cut vector DRAFT — NOT CAM / НЕ ДЛЯ СТАНКА</title>'
         f'<path d="{escape(" ".join(path_data))}" fill="none" stroke="#b91c1c" stroke-width="0.12"/>'
         '<text x="2" y="6" font-size="3" fill="#b91c1c">DRAFT · NO KERF COMPENSATION · NOT FOR CAM</text>'
         '</svg>')
    Path(path).write_text(svg,encoding='utf8')


def main(argv=None):
    pa=argparse.ArgumentParser(description='DRAFT unique shared cut-line preview; NOT CAM or G-code')
    pa.add_argument('input',type=Path)
    pa.add_argument('--svg',type=Path,required=True)
    pa.add_argument('--report',type=Path,required=True)
    args=pa.parse_args(argv)
    data=json.loads(args.input.read_text(encoding='utf-8-sig'))
    report=analyze_shared_boundaries(source_shapes(data))
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    write_preview(report,args.svg,width=data['artboard']['width_mm'],height=data['artboard']['height_mm'])
    print('PREVIEW ONLY (NOT CAM):',report['shared_total_mm'],'mm shared boundary')
    return 0
if __name__=='__main__': raise SystemExit(main())
