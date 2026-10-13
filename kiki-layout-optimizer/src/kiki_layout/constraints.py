"""Per-document positions/rotation permissions and portable option presets.

A constraint references a selected object's original index, name and bounds to
prevent accidental reuse against a different Illustrator selection.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ANGLES = (0, 90, 180, 270)
PRESET_FIELDS = frozenset({"mode", "gap", "margin", "margin_left", "margin_top",
    "margin_right", "margin_bottom", "rotations", "families", "flow",
    "travel_order", "operation", "kerf_mm", "lang",
    "trials", "time_budget_sec", "seed", "advanced_search", "contour_anchors",
    "family_layout", "outline_aware"})


def validate_constraints(data: dict, constraints: dict | None):
    """Return normalized {selection_id: {lock_position, rotations}}."""
    if not constraints:
        return {}
    if constraints.get('schema') != 1:
        raise ValueError('Object constraints: unsupported schema')
    if constraints.get('document_name') != data.get('document_name'):
        raise ValueError('Object constraints belong to another Illustrator document')
    original = {str(o['id']): o for o in data['objects']}
    raw = constraints.get('items', {})
    if not isinstance(raw, dict):
        raise ValueError('Object constraints.items must be an object')
    result = {}
    for key, settings in raw.items():
        key = str(key)
        if key not in original:
            raise ValueError(f'Object constraint refers to missing selection index {key}')
        if not isinstance(settings, dict):
            raise ValueError(f'Invalid object constraint at {key}')
        source = original[key]
        if settings.get('source_name') != source.get('name'):
            raise ValueError(f'Object {key} name changed since constraints were saved; re-export first')
        stored = settings.get('source_bounds_pt')
        actual = source.get('source_bounds_pt')
        if (not isinstance(stored, list) or not isinstance(actual, list) or len(stored) != 4
                or len(actual) != 4 or any(abs(float(a)-float(b)) > 0.05 for a,b in zip(stored, actual))):
            raise ValueError(f'Object {key} changed its bounds; re-export and review constraints')
        lock = settings.get('lock_position', False)
        if not isinstance(lock, bool):
            raise ValueError(f'Object {key} lock_position must be a boolean')
        selected = settings.get('rotations', None)
        if selected is not None:
            if (not isinstance(selected, list) or not selected
                    or any(type(a) is not int or a not in ANGLES for a in selected)):
                raise ValueError(f'Object {key} allowed rotations must be a non-empty list of 0/90/180/270')
            selected = tuple(dict.fromkeys(selected))
        if lock and selected is not None and 0 not in selected:
            raise ValueError(f'Object {key} is position-locked but 0° is forbidden')
        if lock or selected is not None:
            result[key] = {'lock_position': lock, 'rotations': selected}
    return result


def source_centre_mm(obj, data):
    rect = data.get('artboard', {}).get('rect_pt')
    if not isinstance(rect, list) or len(rect) != 4:
        raise ValueError('Position locks need a fresh export including artboard.rect_pt (v0.5+)')
    if any(not math.isfinite(float(x)) for x in rect):
        raise ValueError('Invalid artboard rectangle')
    bounds = obj.get('source_bounds_pt')
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError(f"Object {obj['id']} has no original bounds")
    mm = 25.4 / 72
    return ((float(bounds[0])+float(bounds[2]))/2-float(rect[0]))*mm, (float(rect[1])-(float(bounds[1])+float(bounds[3]))/2)*mm


def constraints_path(input_path: Path) -> Path:
    return Path(input_path).parent / 'constraints.json'


def read_constraints(input_path: Path):
    path = constraints_path(input_path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else None


def save_constraints(input_path: Path, data: dict, items: dict):
    selected = {str(obj['id']): obj for obj in data['objects']}
    entries = {}
    for oid, rule in items.items():
        oid = str(oid)
        if oid not in selected:
            raise ValueError(f'Unknown object ID {oid}')
        if not rule.get('lock_position') and rule.get('rotations') is None:
            continue
        obj = selected[oid]
        entries[oid] = {'source_name':obj.get('name'), 'source_bounds_pt':obj.get('source_bounds_pt'),
                        'lock_position':bool(rule.get('lock_position',False)),
                        'rotations':list(rule['rotations']) if rule.get('rotations') is not None else None}
    payload = {'schema':1, 'document_name':data.get('document_name'), 'items':entries}
    validate_constraints(data, payload)
    path = constraints_path(input_path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_preset(path: Path, options: dict):
    """Presets hold general settings only, never document geometry or locks."""
    preset = {key: (list(value) if isinstance(value, tuple) else value)
              for key,value in options.items() if key in PRESET_FIELDS}
    if preset.get('operation') not in ('engrave','cut'):
        raise ValueError('Invalid preset operation')
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'schema':1,'options':preset},ensure_ascii=False,indent=2),encoding='utf-8')
    return destination


def read_preset(path: Path):
    payload=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if payload.get('schema')!=1 or not isinstance(payload.get('options'),dict):
        raise ValueError('Invalid preset file')
    o=payload['options']
    if set(o)-PRESET_FIELDS or o.get('mode') not in ('dense','uniform','ordered') or o.get('operation') not in ('engrave','cut'):
        raise ValueError('Unsupported preset settings')
    if o.get('rotations') and (not isinstance(o['rotations'],list) or any(x not in ANGLES for x in o['rotations'])):
        raise ValueError('Invalid preset rotation')
    if o.get('family_layout','compact') not in ('compact','family_first'):
        raise ValueError('Invalid preset family layout')
    if 'outline_aware' in o and type(o['outline_aware']) is not bool:
        raise ValueError('Invalid preset outline matching')
    if 'trials' in o and (type(o['trials']) is not int or not 1 <= o['trials'] <= 30):
        raise ValueError('Invalid preset trial count')
    if 'time_budget_sec' in o and (type(o['time_budget_sec']) not in (int,float) or
            not math.isfinite(o['time_budget_sec']) or not 0 <= o['time_budget_sec'] <= 3600):
        raise ValueError('Invalid preset time budget')
    if 'seed' in o and type(o['seed']) is not int:
        raise ValueError('Invalid preset seed')
    if 'contour_anchors' in o and type(o['contour_anchors']) is not bool:
        raise ValueError('Invalid preset contour anchors')
    if 'advanced_search' in o and type(o['advanced_search']) is not bool:
        raise ValueError('Invalid preset advanced search')
    return o
