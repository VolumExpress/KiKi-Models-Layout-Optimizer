"""Disk API behind the desktop UI. No UI or platform-specific code here."""
from __future__ import annotations
import json
import shutil
import re
from pathlib import Path
from .engine import layout
from .cli import svg_preview
from .travel import travel_preview_svg, travel_csv
from .constraints import read_constraints


def project_root() -> Path:
    # src/kiki_layout/gui_jobs.py -> project root
    return Path(__file__).resolve().parents[2]


def document_slug(document_name: str) -> str:
    label = re.sub(r'[/\\:*?"<>|]', '_', document_name)
    label = re.sub(r'(?i)\.ai$', '', label)
    label = re.sub(r'\s+', '_', label)[:72]
    return label or 'Illustrator'


def workspace_for(document_name: str, root: Path | None = None) -> Path:
    return (root or project_root()) / 'workspace' / document_slug(document_name)


def available_exports(root: Path | None = None) -> list[Path]:
    base = (root or project_root()) / 'workspace'
    return sorted(base.glob('*/input_copy.json'), key=lambda p: p.stat().st_mtime, reverse=True)


def calculate(input_path: Path, options: dict, progress=None) -> tuple[dict, dict]:
    """Compute, write to a single document folder, and return result plus geoms.

    Saves to a temporary name first so interrupted runs cannot yield a partially
    serialized file mistakenly accepted by Illustrator.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))
    with input_path.open('r', encoding='utf-8-sig') as file:
        data = json.load(file)
    old_alternatives=input_path.parent/'alternatives'
    if old_alternatives.is_dir(): shutil.rmtree(old_alternatives)
    # Discard a previous result before starting another run: failed calculations
    # must never leave an apparently valid result for the apply script.
    old_result = input_path.parent / "result_test.json"
    if old_result.exists():
        old_result.unlink()
    # Bind document-specific constraints to this exact export. General presets
    # do not include object geometry and therefore remain portable.
    attached = read_constraints(input_path)
    # A checkpoint is never called result_test.json: it must NEVER be
    # mistaken for a validated, explicitly accepted finished calculation.
    checkpoint_file=input_path.parent/'best_so_far.json'
    checkpoint_preview=input_path.parent/'best_so_far.svg'
    for stale in (checkpoint_file,checkpoint_preview):
        if stale.exists(): stale.unlink()
    def on_best(result, shapes):
        tmp=checkpoint_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        tmp.replace(checkpoint_file)
        tmp_svg=checkpoint_preview.with_suffix('.tmp')
        tmp_svg.write_text(svg_preview(shapes,result,lang=options.get('lang','ru')),encoding='utf8')
        tmp_svg.replace(checkpoint_preview)
    alt_dir=input_path.parent/'alternatives'
    if alt_dir.is_dir(): shutil.rmtree(alt_dir)
    all_trials=[]
    def on_trial(index, trial_result, trial_shapes):
        # The files are informational and cannot be applied by the JSX script.
        alt_dir.mkdir(parents=True,exist_ok=True)
        (alt_dir/f'trial_{index:02d}.json').write_text(
            json.dumps(trial_result,ensure_ascii=False,indent=2),encoding='utf8')
        (alt_dir/f'trial_{index:02d}.svg').write_text(
            svg_preview(trial_shapes,trial_result,lang=options.get('lang','ru')),encoding='utf8')
        all_trials.append(index)
    result, geometry = layout(data, **{k:v for k,v in options.items() if k != "lang"},
                              constraints=attached, progress=progress,
                              on_trial=on_trial if options.get('objective_weights') and options.get('trials',1)>1 else None,
                              on_best=on_best if options.get('trials',1)>1 else None)
    if all_trials:
        front=set(result.get('report',{}).get('search',{}).get('pareto_frontier',[]))
        for index in all_trials:
            if index not in front:
                for ext in ('.json','.svg'):
                    (alt_dir/f'trial_{index:02d}{ext}').unlink(missing_ok=True)
        (alt_dir/'pareto_index.json').write_text(json.dumps({
            'schema':1,'source_document':data.get('document_name'),
            'source_export':str(input_path.resolve()),
            'pareto_trials':sorted(front),
            'selected_trial':result['report']['search']['best_trial'],
            'solutions':result['report']['search']['pareto_solutions'],
            'preview_only':True,
        },ensure_ascii=False,indent=2),encoding='utf8')
    folder = input_path.parent
    folder.mkdir(parents=True, exist_ok=True)
    outputs = {
        'result': folder / 'result_test.json',
        'preview': folder / 'preview_test.svg',
        'travel': folder / 'route_test.svg',
        'csv': folder / 'route_test.csv',
    }
    lang = options.get('lang', 'ru')
    tmp = outputs['result'].with_suffix('.tmp')
    try:
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        outputs['preview'].write_text(svg_preview(geometry, result, lang=lang), encoding='utf-8')
        outputs['travel'].write_text(travel_preview_svg(geometry, result), encoding='utf-8')
        outputs['csv'].write_text(travel_csv(result['laser_plan']), encoding='utf-8-sig')
        tmp.replace(outputs['result'])
    finally:
        if tmp.exists():
            tmp.unlink()
    return result, geometry
