from types import SimpleNamespace

from core.knowledge.ike2.compliance import ComplianceResult, evaluate
from core.knowledge.ike2.coverage_os.evidence_chain import (
    build_chain_from_resolve,
    to_audit_bucket,
)
from core.knowledge.ike2.rules import seeded_rules
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict


def test_to_audit_bucket_maps_engine_to_three_buckets():
    assert to_audit_bucket(Verdict.SAFE) == "Safe"
    assert to_audit_bucket(Verdict.FAIL) == "Avoid"
    assert to_audit_bucket(Verdict.UNCERTAIN) == "Depends"
    assert to_audit_bucket(Verdict.WARN) == "Depends"


def test_safe_chain_stores_audit_bucket_not_engine_enum():
    resolved = SimpleNamespace(
        status="resolved", source="truth_anchor",
        resolution_layer="L1_truth_anchor", trusted=True, miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="sugar",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    result = ComplianceResult(
        Verdict.SAFE, [], [], [],
        {("sugar", "hindu_vegetarian"): Verdict.SAFE},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="sugar", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=inp,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Safe"
    assert d["internal_verdict"] == "SAFE"
    assert d["evidence_class"] == "closed_form_plant"
    assert d["rule_ids"] == []


def test_rule_ids_are_rule_identity_filtered_to_this_ingredient():
    """Non-empty multi-ingredient matched_rules — must not leak other atoms' rules."""
    beef = ComplianceInput(
        canonical_name="beef",
        flags={"animal_origin": True, "animal_species": "cow"},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    sugar = ComplianceInput(
        canonical_name="sugar",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "preference", "vegan": "preference"})
    result = evaluate([beef, sugar], profile, seeded_rules())
    assert getattr(result, "matched_rules", None), "evaluate must populate matched_rules"
    beef_ids = [
        m["rule_id"] for m in result.matched_rules
        if m["canonical"] == "beef" and m["restriction"] == "hindu_vegetarian"
    ]
    assert beef_ids
    assert all("hindu_vegetarian" in rid for rid in beef_ids)
    assert any("meat_fish" in rid or "animal" in rid or "species" in rid for rid in beef_ids)
    resolved = SimpleNamespace(
        status="resolved", source="ontology", resolution_layer="L2_local_ontology",
        trusted=True, miss_class=None, group=None,
    )
    chain = build_chain_from_resolve(
        atom="beef", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=beef,
    )
    assert chain.verdict == "Avoid"
    assert chain.rule_ids
    assert all(rid.startswith("hindu_vegetarian:") for rid in chain.rule_ids)
    assert not any(rid.startswith("vegan:") for rid in chain.rule_ids)
    assert "hindu_vegetarian" not in chain.rule_ids

    # Same evaluate result: sugar must NOT inherit Avoid from beef (verdict grain)
    sugar_chain = build_chain_from_resolve(
        atom="sugar", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=sugar,
    )
    assert sugar_chain.verdict == "Safe"
    assert sugar_chain.rule_ids == []


def test_fish_evidence_class_is_allergen_not_only_animal():
    resolved = SimpleNamespace(
        status="resolved", source="truth_anchor",
        resolution_layer="L1_truth_anchor", trusted=True, miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="salmon",
        flags={"animal_origin": True, "fish_source": True, "animal_species": "fish"},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    result = ComplianceResult(
        Verdict.FAIL, ["salmon"], [], [],
        {("salmon", "fish_allergy"): Verdict.FAIL},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="salmon", resolved=resolved, compliance_result=result,
        restriction_id="fish_allergy", compliance_input=inp,
    )
    assert chain.evidence_class == "allergen"
    assert chain.verdict == "Avoid"


def test_uncertain_resolve_marks_insufficient_and_depends():
    resolved = SimpleNamespace(
        status="uncertain", source="unknown_queue",
        resolution_layer="L5_unknown_queue", trusted=False,
        miss_class="M1_absent", group=None,
    )
    result = ComplianceResult(Verdict.UNCERTAIN, [], [], [], {}, matched_rules=[])
    chain = build_chain_from_resolve(
        atom="savills", resolved=resolved, compliance_result=result,
        restriction_id="vegan", compliance_input=None,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Depends"
    assert d["internal_verdict"] == "UNCERTAIN"
    assert d["evidence_class"] == "insufficient"
    assert d["miss_class"] == "M1_absent"


def test_depends_from_uncertainty_can_have_empty_rule_ids():
    """KS/uncertainty Depends is not a trigger — rule_ids may be empty."""
    resolved = SimpleNamespace(
        status="resolved", source="ontology",
        resolution_layer="L2_local_ontology", trusted=True,
        miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="mystery plant",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="DISCOVERED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    result = ComplianceResult(
        Verdict.WARN, [], [], [],
        {("mystery plant", "vegan"): Verdict.WARN},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="mystery plant", resolved=resolved, compliance_result=result,
        restriction_id="vegan", compliance_input=inp,
    )
    assert chain.verdict == "Depends"
    assert chain.rule_ids == []
