"""P11 semantic sorting is explicit, auditable and never a geometry OCR guess."""
import pytest

from kiki_layout import engine
from kiki_layout.semantic_order import sort_semantic_units, validate_manifest


def source():
    objects=[]
    sequence=[("0","P11-SYM-003",3),("1","P11-SYM-001",1),
              ("2","P11-SYM-002",2),("3","P11-SYM-021",1),
              ("4","",None)]
    for oid,code,value in sequence:
        name="P11-SLOT-001__"+code+"__5.5mm__L1" if code else "item-4"
        objects.append({"id":oid,"uuid":"uuid"+oid,"name":name,
                        "geometry":{"type":"path","ring":[[-1,-1],[1,-1],[1,1],[-1,1]]}})
    return {"schema":1,"document_name":"P11_synthetic.ai",
            "artboard":{"width_mm":95,"height_mm":50},
            "objects":objects}


def manifest():
    return {"schema":1,"document_name":"P11_synthetic.ai","entries":{
       "sym:p11-sym-001":{"section":"roman","value":1,"status":"confirmed"},
       "sym:p11-sym-002":{"section":"roman","value":2,"status":"confirmed"},
       "sym:p11-sym-003":{"section":"roman","value":3,"status":"confirmed"},
       "sym:p11-sym-021":{"section":"gothic","value":1,"status":"provisional"}
    }}


def test_semantic_units_sort_by_section_then_numerical_value():
    data=source()
    units=[{"family":str(i),"ids":[str(i)]} for i in (0,3,4,2,1)]
    ordered,audit=sort_semantic_units(units,data["objects"],manifest(),data["document_name"])
    assert [u["family"] for u in ordered]==["1","2","0","3","4"]
    assert audit["mapped_family_count"]==4
    assert audit["unmapped_families"]==["4"]
    assert audit["provisional_families"]==["3"]
    assert audit["strict_sequence"] is True


def test_semantic_engine_placement_is_not_resorted_for_density():
    result,_=engine.layout(source(),mode="uniform",families="named",
                           family_layout="family_first",flow="rows",rotations=(0,),
                           gap=1,margin=2,trials=3,seed=42,
                           semantic_map=manifest())
    assert [x["id"] for x in result["items"]]==["1","2","0","3","4"]
    audit=result["report"]["semantic_order"]
    assert audit["unmapped_families"]
    assert len(result["items"])==5
    assert result["report"]["within_margins"]
    assert result["report"]["min_clearance_mm"]>=1-1e-5
    assert result["report"]["family_layout"]["mode"]=="family_first"


def test_conflicting_semantics_inside_family_fail_closed():
    data=source()
    units=[{"family":"unsafe","ids":["1","2"]}]
    with pytest.raises(ValueError,match="Conflicting semantic identities"):
        sort_semantic_units(units,data["objects"],manifest(),data["document_name"])


def test_semantic_requires_safe_user_options():
    with pytest.raises(ValueError,match="Semantic numbering requires"):
        engine.layout(source(),mode="uniform",families="named",
                      family_layout="compact",semantic_map=manifest())


def test_semantic_must_never_silently_fallback_to_compact(monkeypatch):
    def fail_shelf(data,**kwargs):
        if kwargs.get("semantic_map") is not None:
            raise engine.PackingFailure("Cannot fit family with requested sequence")
        raise AssertionError("Unsorted fallback must not run")
    monkeypatch.setattr(engine,"_layout_once",fail_shelf)
    with pytest.raises(engine.PackingFailure):
        engine.layout(source(),mode="uniform",families="named",
                      family_layout="family_first",semantic_map=manifest(),
                      flow="rows",rotations=(0,),trials=1)


def test_manifest_document_and_value_validation():
    with pytest.raises(ValueError,match="does not match"):
        validate_manifest(manifest(),"wrong_doc.ai")
    invalid=manifest()
    invalid["entries"]["sym:p11-sym-003"]["value"]="3"
    with pytest.raises(ValueError,match="integer"):
        validate_manifest(invalid,"P11_synthetic.ai")
