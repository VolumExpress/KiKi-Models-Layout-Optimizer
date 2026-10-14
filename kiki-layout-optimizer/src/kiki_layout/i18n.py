"""Display-only localization. JSON schema, CLI flag names and geometry are invariant."""
from __future__ import annotations

TEXTS = {
    "ru": {
        "description": "Размещение эмблем по реальным контурам для Adobe Illustrator",
        "input": "JSON, экспортированный через illustrator/export_selection.jsx",
        "output": "Файл JSON с результатом",
        "lang": "Язык сообщений: ru или en (по умолчанию ru)",
        "mode": "Режим размещения: dense, uniform или ordered",
        "gap": "Минимальный зазор между реальными контурами, мм",
        "margin": "Общий отступ от всех четырёх краёв, мм",
        "margin_side": "Отступ от края {side}, мм (переопределяет --margin)",
        "flow": "Раскладка: свободная, по строкам или по столбцам",
        "travel": "Условный порядок обхода (НЕ траектория лазера)",
        "jump": "Порог длинного условного перехода, мм",
        "travel_svg": "SVG-схема условных холостых перемещений",
        "travel_csv": "CSV с условным порядком обхода",
        "width": "Переопределить ширину монтажной области, мм",
        "height": "Переопределить высоту монтажной области, мм",
        "rotations": "Допустимые повороты через запятую: 0,90,180,270",
        "families": "Группировка однотипных эмблем разных размеров",
        "threshold": "Порог совпадения формы (0..1)",
        "no_refine": "Отключить дополнительную оптимизацию размещения",
        "svg": "SVG-предпросмотр в миллиметрах",
        "saved": "Сохранён результат: {path}",
        "svg_saved": "SVG-предпросмотр: {path}",
        "travel_saved": "Схема условных переходов: {path}",
        "csv_saved": "Порядок обхода CSV: {path}",
        "objects": "Объектов",
        "clusters": "Кластеров",
        "gap_actual": "Минимальный фактический зазор, мм",
        "area": "Площадь внешней рамки композиции, мм²",
        "edges": "Соблюдены отступы от краёв",
        "yes": "да", "no": "нет",
        "travel_total": "Условная длина холостых переходов, мм",
        "warnings": "Предупреждения",
        "calc_error": "Не удалось рассчитать раскладку: {error}",
        "w_family": "Автоматические семейства требуют визуальной проверки.",
        "w_contour": "Контуры приближены полилиниями; проверьте геометрию в Illustrator перед изготовлением.",
        "w_laser": "Расчётные переходы между центрами — не траектория станка и не оценка времени.",
    },
    "en": {
        "description": "Contour-aware emblem placement for Adobe Illustrator",
        "input": "JSON exported by illustrator/export_selection.jsx",
        "output": "Output layout JSON file",
        "lang": "Output language: ru or en (default ru)",
        "mode": "Layout mode: dense, uniform or ordered",
        "gap": "Minimum true-contour clearance, mm",
        "margin": "Base clearance from all four edges, mm",
        "margin_side": "Override edge clearance for {side}, mm",
        "flow": "Layout preference: free, rows or columns",
        "travel": "PROXY marking order (NOT an actual laser toolpath)",
        "jump": "Threshold for proxy long jumps, mm",
        "travel_svg": "Optional travel proxy SVG overlay",
        "travel_csv": "Optional proxy marking-order CSV",
        "width": "Override artboard width, mm",
        "height": "Override artboard height, mm",
        "rotations": "Comma-separated subset of 0,90,180,270",
        "families": "Optional same-shape size-family grouping",
        "threshold": "Minimum silhouette similarity (0..1)",
        "no_refine": "Disable layout refinement",
        "svg": "Optional visual SVG preview in mm",
        "saved": "Saved layout: {path}",
        "svg_saved": "SVG preview: {path}",
        "travel_saved": "Travel proxy diagram: {path}",
        "csv_saved": "Travel order CSV: {path}",
        "objects": "Objects",
        "clusters": "Clusters",
        "gap_actual": "Minimum actual clearance, mm",
        "area": "Occupied bounding area, mm²",
        "edges": "Within edge margins",
        "yes": "yes", "no": "no",
        "travel_total": "Proxy travel length, mm",
        "warnings": "Warnings",
        "calc_error": "Layout calculation failed: {error}",
        "w_family": "Automatically detected families require visual confirmation.",
        "w_contour": "Polyline approximation: inspect native Illustrator geometry before fabrication.",
        "w_laser": "Centroid travel proxies are neither laser toolpaths nor time estimates.",
    },
}

WARNING_IDS = (
    ("Auto family detection", "w_family"),
    ("Polyline-based contour approximation", "w_contour"),
    ("Laser jumps are CENTROID-PROXY", "w_laser"),
)


def tr(lang: str, key: str, **kwargs) -> str:
    return TEXTS.get(lang, TEXTS["ru"])[key].format(**kwargs)


def local_warning(lang: str, warning: str) -> str:
    for prefix, key in WARNING_IDS:
        if warning.startswith(prefix):
            return tr(lang, key)
    return warning
