"""Explicit semantic ordering for number plates (never OCR or infer meanings).

A manifest is a local workspace file, not a repository of users' proprietary
symbols. Only explicitly labelled records influence order; unmapped families
are reported and retained in a separate tail section.
"""
from __future__ import annotations

import re

_CODE = re.compile(r"(P\d{2}-SYM-\d{3})(?!\d)", re.I)
_SECTION_RANK = {"roman": 0, "gothic": 1, "carrier": 2, "other": 3}


def validate_manifest(manifest, document_name=None):
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ValueError("Semantic manifest must be a schema=1 JSON object")
    declared = manifest.get("document_name")
    if not isinstance(declared, str) or not declared.strip():
        raise ValueError("Semantic manifest requires document_name")
    if document_name and declared != document_name:
        raise ValueError("Semantic manifest document_name does not match the current export")
    entries = manifest.get("entries")
    if not isinstance(entries, dict) or not entries or len(entries) > 500:
        raise ValueError("Semantic manifest entries must contain 1–500 mappings")
    normalized = {}
    for raw_key, spec in entries.items():
        if not isinstance(raw_key, str) or not (
            re.fullmatch(r"sym:P\d{2}-SYM-\d{3}", raw_key, re.I)
            or re.fullmatch(r"uuid:[\w.-]{1,128}", raw_key)
        ):
            raise ValueError("Semantic manifest keys must be sym:Pxx-SYM-xxx or uuid:<uuid>")
        key = raw_key.lower()
        if key in normalized:
            raise ValueError("Duplicate semantic mapping key")
        if not isinstance(spec, dict) or spec.get("section") not in _SECTION_RANK:
            raise ValueError("Semantic entries need section roman/gothic/carrier/other")
        value = spec.get("value")
        if value is not None and (type(value) is not int or not 1 <= value <= 500):
            raise ValueError("Semantic value must be an integer 1–500 or null")
        if spec.get("section") in ("roman", "gothic") and value is None:
            raise ValueError("Numbered semantic entries need a numeric value")
        status = spec.get("status", "provisional")
        if status not in ("confirmed", "provisional"):
            raise ValueError("Semantic status must be confirmed or provisional")
        normalized[key] = (spec["section"], value, status)
    return normalized


def sort_semantic_units(units, objects, manifest, document_name=None):
    lookup = validate_manifest(manifest, document_name)
    sources = {str(ob["id"]): ob for ob in objects}
    unresolved, provisional, partial, resolved = [], [], [], []
    ordered = []
    for seq, unit in enumerate(units):
        tags = []
        matched = []
        for oid in unit["ids"]:
            ob = sources[oid]
            name = str(ob.get("name", ""))
            m = _CODE.search(name)
            key = "sym:" + m.group(1).lower() if m else None
            uuid = str(ob.get("uuid", ""))
            # UUID-specific entries take precedence over generalized symbol
            # families. They are useful for Illustrator items named item-N.
            meta = lookup.get("uuid:" + uuid.lower()) or (lookup.get(key) if key else None)
            if meta is not None:
                tags.append(meta)
                matched.append(oid)
        distinct = {(section, value) for section, value, _ in tags}
        if len(distinct) > 1:
            raise ValueError("Conflicting semantic identities inside family " + str(unit["family"]))
        if not tags:
            unresolved.append(str(unit["family"]))
            key = (len(_SECTION_RANK), 9999, seq)
        else:
            section, value = next(iter(distinct))
            status = {t[2] for t in tags}
            if "provisional" in status:
                provisional.append(str(unit["family"]))
            if len(matched) != len(unit["ids"]):
                partial.append(str(unit["family"]))
            resolved.append(str(unit["family"]))
            key = (_SECTION_RANK[section], value if value is not None else 9999, seq)
        ordered.append((key, unit))
    ordered.sort(key=lambda pair: pair[0])
    warnings = []
    if unresolved:
        warnings.append(f"{len(unresolved)} unlabeled semantic families placed after mapped numbers; review the manifest.")
    if provisional:
        warnings.append(f"{len(provisional)} semantic families use PROVISIONAL number mappings; confirm against Illustrator.")
    if partial:
        warnings.append(f"{len(partial)} semantic families were partially mapped; verify family detection did not join different symbols.")
    audit = {
        "enabled": True,
        "family_count": len(units),
        "mapped_family_count": len(resolved),
        "unmapped_families": unresolved,
        "provisional_families": provisional,
        "partially_mapped_families": partial,
        "verified_order": "sections roman/gothic/carrier/other, then value; unmapped last",
        "warnings": warnings,
        "strict_sequence": True,
        "source": "explicit workspace semantic_order.json (no OCR)",
    }
    return [unit for _, unit in ordered], audit
