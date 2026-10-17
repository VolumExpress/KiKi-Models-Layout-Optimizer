"""Focused multi-start family-first regressions (no private plate files)."""
from __future__ import annotations

from kiki_layout import engine


def plate():
    objects = []
    ring = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    for n, (symbol, size) in enumerate(
        [('A', 3), ('A', 5.5), ('B', 3), ('B', 5.5), ('C', 3), ('C', 5.5)]
    ):
        objects.append({
            'id': str(n),
            'name': f'Symbol{symbol}__{size}mm',
            'geometry': {'type': 'path',
                         'ring': [[x * size / 2, y * size / 2] for x, y in ring]}
        })
    return {'schema': 1, 'document_name': 'synthetic-P10.ai',
            'artboard': {'width_mm': 85, 'height_mm': 50},
            'objects': objects}


def test_multi_start_explores_distinct_family_wrap_widths(monkeypatch):
    original = engine._layout_once
    inspected = []

    def tracking(source, **options):
        if options.get('family_layout') == 'family_first':
            inspected.append(options['family_width_fraction'])
        return original(source, **options)

    monkeypatch.setattr(engine, '_layout_once', tracking)
    result, _ = engine.layout(plate(), mode='uniform', families='named',
                              family_layout='family_first', flow='rows',
                              gap=1, margin=2, trials=4, seed=42)
    assert inspected == [.55, .40, .32, .65]
    assert result['report']['search']['family_first_requested']
    assert result['report']['family_layout']['mode'] == 'family_first'
    assert result['report']['within_margins']
    assert len(result['items']) == 6
    assert result['report']['min_clearance_mm'] >= 1 - 1e-5


def test_multi_start_prefers_successful_family_ordering_over_compact_score(monkeypatch):
    original = engine._layout_once

    def constructed(source, **options):
        if options.get('family_layout') == 'family_first':
            if options.get('order_strategy') in ('baseline', 'perimeter'):
                raise engine.PackingFailure('Cannot fit family synthetic onto plate with gap 1 mm')
            result, shapes = original(source, **options)
            # A valid family-first layout can have an objectively worse
            # occupied footprint than compact: user preference wins.
            result['report']['occupied_bbox_mm2'] = 1e5
            return result, shapes
        return original(source, **options)

    monkeypatch.setattr(engine, '_layout_once', constructed)
    result, _ = engine.layout(plate(), mode='uniform', families='named',
                              family_layout='family_first', flow='rows',
                              gap=1, margin=2, trials=4, seed=42)
    search = result['report']['search']
    assert search['family_first_preserved'] is True
    assert result['settings']['family_layout'] == 'family_first'
    assert any(t['layout_mode'] == 'compact' for t in search['trial_summaries'])
    assert any(t['layout_mode'] == 'family_first' for t in search['trial_summaries'])
    assert result['report']['within_margins']


def test_legacy_compact_multi_start_is_unmodified():
    source = plate()
    default, _ = engine.layout(source, mode='uniform', families='named',
                               flow='rows', gap=1, margin=2, trials=2)
    explicit, _ = engine.layout(source, mode='uniform', families='named',
                                family_layout='compact',
                                flow='rows', gap=1, margin=2, trials=2)
    # Wall-clock timings are intentionally nondeterministic across CI runners.
    default["report"]["search"].pop("elapsed_sec", None)
    explicit["report"]["search"].pop("elapsed_sec", None)
    assert default == explicit
