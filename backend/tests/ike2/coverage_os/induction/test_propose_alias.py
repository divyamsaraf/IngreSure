from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.propose_alias import propose_alias


def _ont(*rows):
    return {"ingredients": list(rows)}


def test_unique_head_resolves_to_alias_proposal():
    ontology = _ont({"canonical_name": "broccoli", "plant_origin": True})
    item = ClusterItem("broccoli florets", "broccoli florets", 5, "M4_morphology")
    cand = propose_alias(item, ontology=ontology, alias_table={})
    assert cand is not None
    assert cand.proposal_kind == "variant_alias"
    assert cand.canonical == "broccoli"
    assert cand.safety_class == "plant_closed"


def test_ambiguous_or_missing_yields_no_proposal():
    # Two-token raw where each single-token drop hits a different ontology row
    # → len(targets) == 2 → no proposal (ambiguous branch).
    ontology = _ont(
        {"canonical_name": "apple", "plant_origin": True},
        {"canonical_name": "vinegar", "plant_origin": True},
    )
    ambiguous = ClusterItem("apple vinegar", "apple vinegar", 3, "M1_absent")
    assert propose_alias(ambiguous, ontology=ontology, alias_table={}) is None
    # Zero closed-form targets.
    missing = ClusterItem("zzzz unknown", "zzzz unknown", 3, "M1_absent")
    assert propose_alias(missing, ontology=ontology, alias_table={}) is None


def test_already_aliased_no_proposal():
    ontology = _ont({"canonical_name": "salt", "plant_origin": True})
    item = ClusterItem("salt himalayan", "salt himalayan", 4, "M1_absent")
    assert (
        propose_alias(
            item,
            ontology=ontology,
            alias_table={"salt himalayan": "salt"},
        )
        is None
    )
