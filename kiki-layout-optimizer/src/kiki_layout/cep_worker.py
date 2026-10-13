"""CEP headless worker: newline-delimited JSON progress, no Tk/COM/UI.

Only the locally installed CEP adapter starts this process. One request JSON file
specifies an input export and normal layout options, never executable commands.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import traceback
from pathlib import Path
from .gui_jobs import calculate

ALLOWED = {"mode", "gap", "margin", "margin_left", "margin_top", "margin_right",
           "margin_bottom", "rotations", "families", "flow", "travel_order",
           "operation", "kerf_mm", "lang", "trials", "time_budget_sec", "seed", "contour_anchors", "advanced_geometry", "advanced_search", "objective_weights", "guided_objectives", "cut_common_line_audit", "family_layout", "outline_aware"}
STAGES = {"searching": (3, 95), "compacting": (92, 97), "preparing": (0, 3), "placing": (3, 80), "refining": (80, 92),
          "validating": (97, 99), "complete": (99, 99)}


def emit(kind: str, **data):
    print(json.dumps({"kind":kind, **data}, ensure_ascii=False), flush=True)


def parse_request(path: Path):
    request = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(request, dict) or request.get("schema") != 1:
        raise ValueError("Unsupported CEP calculation request")
    input_path = Path(request.get("input", "")).resolve()
    if input_path.name != "input_copy.json" or input_path.parent.parent.name != "workspace":
        raise ValueError("Input must be an Illustrator export in a KiKi workspace")
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    options = request.get("options")
    if not isinstance(options, dict) or set(options) - ALLOWED:
        raise ValueError("Unsupported or invalid calculation options")
    if not isinstance(options.get("rotations"), list) or not options["rotations"]:
        raise ValueError("Rotation list must not be empty")
    options["rotations"] = tuple(options["rotations"])
    if options.get("family_layout", "compact") not in ("compact","family_first"):
        raise ValueError("Invalid family layout policy")
    if "outline_aware" in options and type(options["outline_aware"]) is not bool:
        raise ValueError("outline_aware must be boolean")
    if "trials" in options and (type(options["trials"]) is not int or not 1 <= options["trials"] <= 30):
        raise ValueError("trials must be an integer from 1 to 30")
    if "time_budget_sec" in options and (type(options["time_budget_sec"]) not in (int,float) or
            not math.isfinite(options["time_budget_sec"]) or not 0 <= options["time_budget_sec"] <= 3600):
        raise ValueError("invalid time budget")
    if "seed" in options and type(options["seed"]) is not int:
        raise ValueError("seed must be integer")
    if "contour_anchors" in options and type(options["contour_anchors"]) is not bool:
        raise ValueError("contour_anchors must be boolean")
    if "advanced_geometry" in options and type(options["advanced_geometry"]) is not bool:
        raise ValueError("advanced_geometry must be boolean")
    if "advanced_search" in options and type(options["advanced_search"]) is not bool:
        raise ValueError("advanced_search must be boolean")
    from .multiobjective import normalized_weights
    normalized_weights(options.get('objective_weights'))
    if 'guided_objectives' in options and type(options['guided_objectives']) is not bool:
        raise ValueError('guided_objectives must be boolean')
    if 'cut_common_line_audit' in options and type(options['cut_common_line_audit']) is not bool:
        raise ValueError('cut_common_line_audit must be boolean')
    return input_path, options


def run(path: Path):
    input_path, options = parse_request(path)
    last = [-1]
    def progress(stage, done, total):
        lo, hi = STAGES.get(stage, (0, 0))
        value = max(0, min(99, int(lo + (hi-lo) * done / max(total,1))))
        if value != last[0] or stage == 'complete':
            last[0] = value
            emit("progress", stage=stage, done=done, total=total, percent=value)
    emit("started", input=str(input_path), document=input_path.parent.name)
    result, _ = calculate(input_path, options, progress=progress)
    report=result["report"]
    emit("complete", percent=100, report={
        "object_count":report["object_count"], "cluster_count":report["cluster_count"],
        "min_clearance_mm":report["min_clearance_mm"],
        "occupied_bbox_mm2":report["occupied_bbox_mm2"],
        "within_margins":report["within_margins"],
        "search":report.get("search",{}),
        "advanced_geometry":report.get("advanced_geometry",{}),
        "advanced_search":report.get("advanced_search",{}),
        "family_audit":report.get("family_audit",[]),
        "family_layout":report.get("family_layout",{}),
        "warnings":report.get("warnings", []),
        "multiobjective": report.get("multiobjective",{}),
        "pareto_frontier":report.get("search",{}).get("pareto_solutions",[]),
        "common_line_audit": report.get("common_line_audit",{})},
        folder=str(input_path.parent), result=str(input_path.parent / 'result_test.json'),
        preview=str(input_path.parent / 'preview_test.svg'))


def main(argv=None):
    parser=argparse.ArgumentParser(description="KiKi headless CEP layout worker")
    parser.add_argument("request", type=Path)
    args=parser.parse_args(argv)
    try:
        run(args.request)
        return 0
    except Exception as exc:
        emit("error", message=str(exc), type=exc.__class__.__name__)
        return 1

if __name__ == '__main__':
    sys.exit(main())
