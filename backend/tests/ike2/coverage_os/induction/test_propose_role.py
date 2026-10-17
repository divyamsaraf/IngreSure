from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.propose_role import (
    propose_role_backfill,
    propose_role_pattern_fill,
)
from core.knowledge.ike2.coverage_os.neutralize import build_role_index


def test_pattern_fill_proposes_empty_plant_mod_beside_dairy_head():
    ontology = {
        "ingredients": [
            {"canonical_name": "yogurt", "role": "dairy_head", "dairy_source": True, "animal_origin": True},
            {"canonical_name": "oat", "plant_origin": True},  # empty role
        ]
    }
    role_index = build_role_index(ontology["ingredients"])
    item = ClusterItem("oat yogurt", "oat yogurt", 8, "M6_dairy_variety")
    cand = propose_role_pattern_fill(item, ontology=ontology, role_index=role_index)
    assert cand is not None
    assert cand.proposal_kind == "ontology_role"
    assert cand.canonical == "oat"
    assert cand.role == "plant_mod"
    assert cand.safety_class == "plant_closed"


def test_backfill_from_tear_evidence():
    ontology = {
        "ingredients": [
            {"canonical_name": "vinegar", "plant_origin": True},
        ]
    }
    cands = propose_role_backfill(
        ontology=ontology,
        tear_evidence={"vinegar": "culinary_keep"},
    )
    assert len(cands) == 1
    assert cands[0].role == "culinary_keep"
    assert cands[0].safety_class == "plant_closed"


def test_no_role_proposal_without_existing_row():
    ontology = {"ingredients": [{"canonical_name": "yogurt", "role": "dairy_head", "dairy_source": True}]}
    role_index = build_role_index(ontology["ingredients"])
    item = ClusterItem("cashew yogurt", "cashew yogurt", 5, "M1_absent")
    assert propose_role_pattern_fill(item, ontology=ontology, role_index=role_index) is None
