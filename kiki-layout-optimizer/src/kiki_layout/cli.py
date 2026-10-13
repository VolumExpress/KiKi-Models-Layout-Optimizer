"""Command-line entry point and static SVG preview."""
import argparse
import html
import json
import sys
from .i18n import tr, local_warning
from pathlib import Path
from .engine import layout
from .travel import travel_preview_svg, travel_csv
from .constraints import read_constraints


def svg_preview(geometry, result, lang="ru"):
    width=result["artboard"]["width_mm"]
    height=result["artboard"]["height_mm"]
    texts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}">',
           f'<rect width="{width}" height="{height}" fill="white" stroke="#999"/>']
    edges=result.get("settings",{}).get("margins_mm")
    if edges:
        safe_w=width-edges["left"]-edges["right"]
        safe_h=height-edges["top"]-edges["bottom"]
        texts.append(f'<rect x="{edges["left"]}" y="{edges["top"]}" width="{safe_w}" height="{safe_h}" fill="none" stroke="#d9534f" stroke-dasharray="0.7 0.7" stroke-width="0.15"><title>{"Рабочая область пластины" if lang=="ru" else "Usable layout area"}</title></rect>')
    palette=["#467BB4","#B46F46","#4C9B7D","#9F77B1","#A3A152","#C65B74"]
    for i,(oid,shape) in enumerate(geometry.items()):
        # Polygon and MultiPolygon, with separate paths for the interiors.
        polys=list(shape.geoms) if hasattr(shape,"geoms") else [shape]
        pieces=[]
        for p in polys:
            if not hasattr(p,"exterior"):
                continue
            for ring in [p.exterior]+list(p.interiors):
                coords=list(ring.coords)
                if not coords: continue
                pieces.append("M "+" L ".join(f"{x:.3f} {y:.3f}" for x,y in coords)+" Z")
        path=" ".join(pieces)
        texts.append(f'<path d="{path}" fill="{palette[i%len(palette)]}" fill-opacity="0.65" '
                     f'stroke="#292929" stroke-width="0.09" fill-rule="evenodd"><title>{html.escape(oid)}</title></path>')
    texts.append('</svg>')
    return "\n".join(texts)


def main(argv=None):
    # Determine help language even when --lang is located AFTER --help or input.
    cli = list(argv) if argv is not None else sys.argv[1:]
    lang = "ru"
    for i, token in enumerate(cli):
        if token.startswith("--lang="):
            lang = token.partition("=")[2]
        elif token == "--lang" and i + 1 < len(cli):
            lang = cli[i+1]
    if lang not in ("ru", "en"):
        lang = "ru"  # argparse will validate the invalid --lang value itself
    parser=argparse.ArgumentParser(description=tr(lang,"description"))
    parser.add_argument("input", type=Path, help=tr(lang,"input"))
    parser.add_argument("-o","--output",type=Path,default=Path("layout.json"),help=tr(lang,"output"))
    parser.add_argument("--lang", choices=["ru","en"],default="ru",help=tr(lang,"lang"))
    parser.add_argument("--operation",choices=["engrave","cut"],default="engrave")
    parser.add_argument("--kerf-mm",type=float,default=0.0)
    parser.add_argument("--mode",choices=["dense","uniform","ordered"],default="uniform",help=tr(lang,"mode"))
    parser.add_argument("--gap",type=float,default=0.8,help=tr(lang,"gap"))
    parser.add_argument("--margin",type=float,default=2.0,help=tr(lang,"margin"))
    for side in ("left", "top", "right", "bottom"):
        parser.add_argument("--margin-"+side,type=float,default=None,
                            help=tr(lang,"margin_side",side=side))
    parser.add_argument("--flow",choices=["free","rows","columns"],default="free",
                        help=tr(lang,"flow"))
    parser.add_argument("--travel-order",choices=["source","nearest","rows","columns"],
                        default="nearest",help=tr(lang,"travel"))
    parser.add_argument("--long-jump",type=float,default=15.0,help=tr(lang,"jump"))
    parser.add_argument("--travel-svg",type=Path,help=tr(lang,"travel_svg"))
    parser.add_argument("--travel-csv",type=Path,help=tr(lang,"travel_csv"))
    parser.add_argument("--width",type=float,help=tr(lang,"width"))
    parser.add_argument("--height",type=float,help=tr(lang,"height"))
    parser.add_argument("--rotations",default="0",help=tr(lang,"rotations"))
    parser.add_argument("--families",choices=["off","named","auto"],default="off",
                        help=tr(lang,"families"))
    parser.add_argument("--outline-aware",action="store_true",help="Opt-in outline-thickness insensitive matching")
    parser.add_argument("--family-layout",choices=["compact","family_first"],default="compact",
                        help="Compact packing or visually ordered family sections")
    parser.add_argument("--family-threshold",type=float,default=0.97,help=tr(lang,"threshold"))
    parser.add_argument("--no-refine",action="store_true",help=tr(lang,"no_refine"))
    parser.add_argument("--trials",type=int,default=1,help="Multistart runs: 1 to 30")
    parser.add_argument("--time-budget",type=float,default=0.,help="Soft search time budget in seconds (0 = no limit)")
    parser.add_argument("--seed",type=int,default=42,help="Deterministic search seed")
    parser.add_argument("--contour-anchors",action="store_true",help="Experimental vertex anchors, NOT exact NFP")
    parser.add_argument("--advanced-search",action="store_true",help="Python LNS + beam local repacking")
    parser.add_argument("--advanced-geometry",action="store_true",help="v0.6.2: bounded concave NFP anchors and beam group repack")
    parser.add_argument('--weight-area',type=float,default=None,help='Multi-objective weight 0–10; requires all three weights')
    parser.add_argument('--weight-spacing',type=float,default=None,help='Gap uniformity weight 0–10')
    parser.add_argument('--weight-travel',type=float,default=None,help='Centroid travel proxy weight 0–10')
    parser.add_argument('--guided-objectives',action='store_true',help='EXPERIMENTAL: guide packing candidate positions with objective weights')
    parser.add_argument('--common-line-audit',action='store_true',help='Inspection only, cutting input boundaries; not CAM')
    parser.add_argument("--svg",type=Path,help=tr(lang,"svg"))
    parser.add_argument("--no-constraints",action="store_true",help="Ignore document constraints.json")
    args=parser.parse_args(cli)
    lang=args.lang
    try:
        data=json.loads(args.input.read_text(encoding="utf-8-sig"))
        rotation_values=tuple(int(x.strip()) for x in args.rotations.split(","))
        requested=(args.weight_area,args.weight_spacing,args.weight_travel)
        if any(v is not None for v in requested) and not all(v is not None for v in requested):
            raise ValueError('Set all three objective weights or none')
        obj_weights=(dict(area=requested[0],spacing=requested[1],travel=requested[2])
                     if all(v is not None for v in requested) else None)
        result,geoms=layout(data,mode=args.mode,gap=args.gap,margin=args.margin,
                            objective_weights=obj_weights,guided_objectives=args.guided_objectives,cut_common_line_audit=args.common_line_audit,
                            trials=args.trials,time_budget_sec=args.time_budget,
                            seed=args.seed,contour_anchors=args.contour_anchors,advanced_geometry=args.advanced_geometry,advanced_search=args.advanced_search,
                            operation=args.operation,kerf_mm=args.kerf_mm,
                            rotations=rotation_values,families=args.families,
                            family_threshold=args.family_threshold,family_layout=args.family_layout,outline_aware=args.outline_aware,
                            width=args.width,height=args.height,refine=not args.no_refine,
                            margin_left=args.margin_left,margin_top=args.margin_top,
                            margin_right=args.margin_right,margin_bottom=args.margin_bottom,
                            flow=args.flow,travel_order=args.travel_order,
                            long_jump_mm=args.long_jump,
                            constraints=None if args.no_constraints else read_constraints(args.input))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        if args.svg:
            args.svg.parent.mkdir(parents=True,exist_ok=True)
            args.svg.write_text(svg_preview(geoms,result,lang=lang),encoding="utf-8")
        if args.travel_svg:
            args.travel_svg.parent.mkdir(parents=True,exist_ok=True)
            args.travel_svg.write_text(travel_preview_svg(geoms,result),encoding="utf-8")
        if args.travel_csv:
            args.travel_csv.parent.mkdir(parents=True,exist_ok=True)
            args.travel_csv.write_text(travel_csv(result["laser_plan"]),encoding="utf-8-sig")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2,tr(lang,"calc_error",error=str(exc))+"\n")
    report=result["report"]
    print(tr(lang,"objects")+":",report["object_count"])
    print(tr(lang,"clusters")+":",report["cluster_count"])
    print(tr(lang,"gap_actual")+":",report["min_clearance_mm"])
    print(tr(lang,"area")+":",report["occupied_bbox_mm2"])
    print(tr(lang,"edges")+":",tr(lang,"yes") if report["within_margins"] else tr(lang,"no"))
    print(tr(lang,"travel_total")+":",report["travel_proxy"]["travel_total_mm"])
    if report.get("warnings"):
        print(tr(lang,"warnings")+":")
        for w in report["warnings"]:
            print("  •",local_warning(lang,w))
    print(tr(lang,"saved",path=args.output))
    if args.svg:
        print(tr(lang,"svg_saved",path=args.svg))
    if args.travel_svg:
        print(tr(lang,"travel_saved",path=args.travel_svg))
    if args.travel_csv:
        print(tr(lang,"csv_saved",path=args.travel_csv))

if __name__=="__main__":
    main()
