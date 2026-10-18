"""Native merge/split family grouping regressions across KiKi plate structures.

User artwork remains private. UUID partitions are validated and only alter
logical nesting groups, never physical geometry or Illustrator source files.
"""
import copy
import pytest

from kiki_layout.family_override import apply_family_overrides
from kiki_layout import engine


def source():
    objects=[]
    for i,(w,h) in enumerate([(1.5,1.8),(2.3,2.0),(1.2,1.7),(2.7,3.1),(3.2,3.5),(1.0,1.2)]):
        objects.append({"id":str(i),"uuid":f"uuid-{i}","name":f"item-{i}",
            "geometry":{"type":"path","ring":[[-w,-h],[w,-h],[w,h],[-w,h]]}})
    return {"schema":1,"document_name":"P11-synthetic.ai",
            "artboard":{"width_mm":145,"height_mm":95},"objects":objects}


def overrides(*groups):
    return {"schema":1,"document_name":"P11-synthetic.ai",
            "groups":[{"id":f"g{i}","uuids":list(g)} for i,g in enumerate(groups)]}


def test_merging_two_geometric_families_preserves_all_individual_shapes():
    data=source()
    frozen=copy.deepcopy(data)
    partition=overrides(["uuid-0","uuid-1","uuid-2"],["uuid-3","uuid-4"],["uuid-5"])
    labels=apply_family_overrides(data,partition)
    assert labels["0"] == labels["2"]
    assert labels["0"] != labels["3"]
    result,_=engine.layout(data,mode="uniform",families="auto",
        family_layout="family_first",flow="rows",rotations=(0,),
        gap=4.5,margin=3,trials=2,family_overrides=partition)
    assert len(result["items"])==len(data["objects"])
    assert result["report"]["cluster_count"]==3
    assert result["report"]["within_margins"]
    assert result["report"]["min_clearance_mm"]>=4.5-1e-5
    assert {i["source_uuid"] for i in result["items"]}=={o["uuid"] for o in data["objects"]}
    assert data==frozen


def test_splitting_existing_group_changes_only_logical_membership():
    data=source()
    initial=overrides(["uuid-0","uuid-1","uuid-2"],["uuid-3","uuid-4","uuid-5"])
    split=overrides(["uuid-0","uuid-2"],["uuid-1"],["uuid-3","uuid-4","uuid-5"])
    assert apply_family_overrides(data,initial)["0"]==apply_family_overrides(data,initial)["1"]
    assert apply_family_overrides(data,split)["0"]!=apply_family_overrides(data,split)["1"]
    result,_=engine.layout(data,mode="uniform",families="auto",
        family_layout="family_first",flow="rows",rotations=(0,),
        gap=4.5,margin=3,trials=2,family_overrides=split)
    assert result["report"]["cluster_count"]==3
    assert len(result["items"])==6


@pytest.mark.parametrize("bad",[
    overrides(["uuid-0","uuid-1"],["uuid-2","uuid-3"]), # missing 4,5
    overrides(["uuid-0","uuid-1"],["uuid-1","uuid-2"],["uuid-3","uuid-4","uuid-5"]), # duplicate
    overrides(["uuid-0","uuid-1","uuid-2"],["uuid-3","uuid-4","uuid-MISSING"]), # stale export
    {"schema":1,"document_name":"P01-OTHER.ai","groups":[{"id":"group","uuids":["uuid-0"]}]},
    {"schema":1,"document_name":"P11-synthetic.ai","groups":[
       {"id":"same","uuids":["uuid-0"]},{"id":"same","uuids":["uuid-1"]}]},
])
def test_invalid_or_stale_uuid_partition_is_rejected(bad):
    with pytest.raises(ValueError):
        apply_family_overrides(source(),bad)


def test_p11_duplicate_numerals_merge_without_conflicting_semantics():
    data=source()
    partition=overrides(["uuid-0","uuid-1","uuid-2"],["uuid-3","uuid-4","uuid-5"])
    entries={f"uuid:uuid-{i}":{"section":"roman",
               "value":14 if i<3 else 16,
               "priority":0 if i<3 else 1,"status":"confirmed"} for i in range(6)}
    manifest={"schema":1,"document_name":data["document_name"],"entries":entries}
    result,_=engine.layout(data,mode="uniform",families="auto",family_layout="family_first",
        flow="rows",rotations=(0,),gap=4.5,margin=3,trials=2,
        family_overrides=partition,semantic_map=manifest)
    assert len(result["items"])==6
    assert result["report"]["semantic_order"]["mapped_family_count"]==2
    assert not result["report"]["semantic_order"]["unmapped_families"]
    assert result["report"]["within_margins"]
