"""Universal family editor contracts across four plate domains.

Synthetic fixtures only; the actual KiKi artwork never enters public GitHub.
These check domain neutrality of the plan, stable UUID mapping, and geometry.
"""
from __future__ import annotations

import pytest

from kiki_layout import engine
from kiki_layout.semantic_order import sort_semantic_units, validate_manifest


@pytest.mark.parametrize("plate,descriptors", [
    ("P01_Ultramarines_Editable_Layout.ai", [
        ("P01-SYM-001","chapter",2),("P01-SYM-002","chapter",1),
        ("item-unnamed","other",3)]),
    ("P03_Dark_Angels_Editable_Layout.ai", [
        ("item-angel","chapter",3),("item-wing","chapter",1),
        ("P03-SYM-009","chapter",2)]),
    ("P10_Roles_Honours_Editable_Layout.ai", [
        ("item-role","role",2),("P10-SYM-011","role",1),
        ("item-honour","other",3)]),
    ("P11_Numbers_Squads_Editable_Layout.ai", [
        ("P11-SYM-001","roman",1),("item-XI","roman",11),
        ("P11-SYM-021","gothic",1)]),
])
def test_all_four_plate_domains_support_native_family_metadata(plate, descriptors):
    objects=[]
    entries={}
    for group, (symbol, section, priority) in enumerate(descriptors):
        for variant in range(2):
            uid=f"uid-{plate[:3]}-{group}-{variant}"
            objid=str(group*2+variant)
            size=1.5+variant*0.4
            objects.append({"id":objid,"uuid":uid,
              "name":f"P11-SLOT-001__{symbol}__5.5mm__L1",
              "geometry":{"type":"path","ring":[[-size,-size],[size,-size],
                    [size,size],[-size,size]]}})
            entries["uuid:"+uid.lower()]={
              "section":section,"value":priority if section in ("roman","gothic") else None,
              "priority":priority,"status":"confirmed"}
    source={"schema":1,"document_name":plate,"source_selection_count":len(objects),
       "artboard":{"width_mm":145,"height_mm":95},"objects":objects}
    manifest={"schema":1,"document_name":plate,"entries":entries}
    assert len(validate_manifest(manifest,plate)) == len(objects)
    # Group two different sizes under the same logical family, independent of glyph identity.
    units=[{"family":str(i),"ids":[str(i*2),str(i*2+1)]} for i in range(3)]
    ordered,audit=sort_semantic_units(units,objects,manifest,plate)
    assert [int(u["family"]) for u in ordered] == sorted(
       range(3),key=lambda i:(
         {"roman":0,"gothic":1,"chapter":2,"role":3,"carrier":4,"other":5}[descriptors[i][1]],
         descriptors[i][2]))
    assert audit["mapped_family_count"]==3
    assert not audit["unmapped_families"]
    result,_=engine.layout(source,mode="uniform",families="off",
        family_layout="family_first",flow="rows",rotations=(0,),
        gap=2,margin=3,trials=2,seed=42,semantic_map=manifest)
    assert len(result["items"])==len(objects)
    assert {it["source_uuid"] for it in result["items"]} == {ob["uuid"] for ob in objects}
    assert result["report"]["within_margins"]
    assert result["report"]["min_clearance_mm"] >= 2 - 1e-5
    assert result["report"]["semantic_order"]["mapped_family_count"]==len(objects)
    assert not result["report"]["semantic_order"]["provisional_families"]


def test_reexport_requires_matching_document_name():
    plan={"schema":1,"document_name":"P01_Ultramarines_Editable_Layout.ai",
          "entries":{"uuid:uuid-42":{"section":"chapter","value":None,
                    "priority":7,"status":"provisional"}}}
    with pytest.raises(ValueError,match="does not match"):
        validate_manifest(plan,"P03_Dark_Angels_Editable_Layout.ai")


def test_conflicting_uuid_values_in_detected_family_fail_closed():
    objects=[{"id":"0","uuid":"a","name":"item-0"},{"id":"1","uuid":"b","name":"item-1"}]
    plan={"schema":1,"document_name":"P10.ai","entries":{
         "uuid:a":{"section":"role","value":None,"priority":1,"status":"confirmed"},
         "uuid:b":{"section":"role","value":None,"priority":2,"status":"confirmed"}}}
    with pytest.raises(ValueError,match="Conflicting semantic identities"):
        sort_semantic_units([{"family":"mixed","ids":["0","1"]}],objects,plan,"P10.ai")
