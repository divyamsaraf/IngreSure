"""The resolver -> compliance seam: flatten a ResolvedIngredient into the shape
compliance.evaluate reads. This is where mapped group flags start protecting
users, so the flattening must be lossless and fail-closed."""
from types import SimpleNamespace

from core.knowledge.ike2.resolver import ResolvedIngredient
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.truth_anchor import TruthAnchorFact


def _resolved(group, *, trusted=True, status="resolved", source="db", layer="L3_db_alias"):
    return ResolvedIngredient(
        group=group, source=source, confidence_band="high",
        trusted=trusted, resolution_layer=layer, status=status,
    )


def test_db_group_flattens_flags_and_metadata():
    # A db GroupRow exposes every column as a flat attribute (select("*")).
    group = SimpleNamespace(
        canonical_name="peanut butter", peanut_source=True, tree_nut_source=False,
        knowledge_state="AUTO_CLASSIFIED", alcohol_role="none", alcohol_content=None,
        verdict_cap=None, uncertainty_flags=[],
    )
    ci = to_compliance_input(_resolved(group))
    assert ci.canonical_name == "peanut butter"
    assert ci.flags["peanut_source"] is True
    assert ci.flags["tree_nut_source"] is False
    assert ci.knowledge_state == "AUTO_CLASSIFIED"
    assert ci.trusted is True
    assert ci.alcohol_role == "none"
    assert ci.trace is False


def test_db_group_carries_verdict_cap_and_trust():
    group = SimpleNamespace(
        canonical_name="spices", animal_origin=False, knowledge_state="VERIFIED",
        verdict_cap="WARN", alcohol_role=None, uncertainty_flags=[],
    )
    ci = to_compliance_input(_resolved(group, trusted=False))
    assert ci.verdict_cap == "WARN"
    assert ci.trusted is False


def test_truth_anchor_fact_flattens_flags_dict():
    fact = TruthAnchorFact(canonical_name="gelatin", flags={"animal_origin": True})
    ci = to_compliance_input(_resolved(fact, source="truth_anchor", layer="L1_truth_anchor"))
    assert ci.flags["animal_origin"] is True
    assert ci.knowledge_state == "LOCKED"
    assert ci.canonical_name == "gelatin"


def test_truth_anchor_alcohol_content_derives_ingredient_role():
    # The ethanol anchor carries alcohol_content, not alcohol_role; compliance keys
    # off alcohol_role, so the seam must derive it or alcohol users get a false-SAFE.
    fact = TruthAnchorFact(canonical_name="ethanol", flags={"alcohol_content": 1.0})
    ci = to_compliance_input(_resolved(fact, source="truth_anchor", layer="L1_truth_anchor"))
    assert ci.alcohol_role == "ingredient"


def test_uncertain_resolution_is_fail_closed():
    r = ResolvedIngredient(
        group=None, source="unknown_queue", confidence_band="none",
        trusted=False, resolution_layer="L5_unknown_queue", status="uncertain",
    )
    ci = to_compliance_input(r)
    assert ci.flags == {}
    assert ci.knowledge_state == "UNCLASSIFIED"
    assert ci.trusted is False
    assert ci.alcohol_role is None


def test_trace_flag_passes_through():
    group = SimpleNamespace(
        canonical_name="peanut", peanut_source=True, tree_nut_source=False,
        knowledge_state="VERIFIED", alcohol_role="none", alcohol_content=None,
        verdict_cap=None, uncertainty_flags=[],
    )
    ci = to_compliance_input(_resolved(group), trace=True)
    assert ci.trace is True
