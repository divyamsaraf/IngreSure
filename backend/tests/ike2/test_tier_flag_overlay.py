"""Layer integrity: Tier-2/DB AUTO_CLASSIFIED must not defeat Tier-1 LOCKED safety flags."""
from types import SimpleNamespace

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.compliance import _effective_flags, evaluate
from core.knowledge.ike2.resolver import ResolvedIngredient
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology
from core.knowledge.ike2.truth_anchor import TruthAnchorFact
from core.knowledge.ike2.verdict import Verdict, to_external


def _degraded_group(atom: str, clear_flags: tuple[str, ...]) -> TruthAnchorFact:
    """Simulate a stale ontology/DB row that omits curated safety bits."""
    t2 = local_ontology.lookup(atom)
    assert t2 is not None
    flags = dict(t2.flags)
    for f in clear_flags:
        flags[f] = False
    return TruthAnchorFact(
        canonical_name=t2.canonical_name,
        flags=flags,
        knowledge_state="AUTO_CLASSIFIED",
    )


def test_effective_flags_overlays_locked_tier1_onto_auto_classified():
    """C1 must heal ontology/DB rows that omit allergen flags (AUTO_CLASSIFIED)."""
    deg = _degraded_group("gelatin", ("fish_source",))
    assert deg.flags.get("fish_source") is not True

    r = SimpleNamespace(
        canonical_name=deg.canonical_name,
        flags=dict(deg.flags),
        knowledge_state=deg.knowledge_state,
    )
    eff = _effective_flags(r)
    t1 = ta.lookup("gelatin")
    assert t1 is not None and t1.flags.get("fish_source") is True
    assert eff.get("fish_source") is True, eff


def test_tier2_gelatin_still_fails_fish_allergy_via_tier1_overlay():
    deg = _degraded_group("gelatin", ("fish_source",))
    ri = ResolvedIngredient(
        group=deg,
        source="local_ontology",
        confidence_band="high",
        trusted=True,
        resolution_layer="L2_local_ontology",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="gelatin")
    profile = SimpleNamespace(restrictions={"fish_allergy": "medical"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert to_external(result.verdict) == "NOT_SAFE"
    assert result.verdict == Verdict.FAIL


def test_tier2_honey_safe_for_hindu_veg_via_bee_product_overlay():
    """Simulate a stale DB/ontology row that still lacks bee_product."""
    deg = _degraded_group("honey", ("bee_product",))
    assert not deg.flags.get("bee_product")
    ri = ResolvedIngredient(
        group=deg,
        source="local_ontology",
        confidence_band="high",
        trusted=True,
        resolution_layer="L2_local_ontology",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="honey")
    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "medical"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert to_external(result.verdict) == "SAFE"
    # Overlay must also keep Jain Avoid (bee_product from Tier-1).
    jain = evaluate(
        [ci],
        SimpleNamespace(restrictions={"jain": "medical"}),
        rules_module.seeded_rules(),
    )
    assert to_external(jain.verdict) == "NOT_SAFE"


def test_tier2_fish_fails_fish_allergy_via_overlay():
    deg = _degraded_group("tuna", ("fish_source",))
    assert deg.flags.get("fish_source") is not True
    ri = ResolvedIngredient(
        group=deg,
        source="local_ontology",
        confidence_band="high",
        trusted=True,
        resolution_layer="L2_local_ontology",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="tuna")
    profile = SimpleNamespace(restrictions={"fish_allergy": "medical"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert to_external(result.verdict) == "NOT_SAFE"


def test_tier2_shrimp_fails_shellfish_allergy_via_overlay():
    deg = _degraded_group("shrimp", ("shellfish_source",))
    assert deg.flags.get("shellfish_source") is not True
    ri = ResolvedIngredient(
        group=deg,
        source="local_ontology",
        confidence_band="high",
        trusted=True,
        resolution_layer="L2_local_ontology",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="shrimp")
    profile = SimpleNamespace(restrictions={"shellfish_allergy": "medical"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert to_external(result.verdict) == "NOT_SAFE"


def test_e910_uncertain_not_overwritten_by_blunt_cysteine_overlay():
    """E910 → l-cysteine with verdict_cap WARN must stay Depends for vegan."""
    from core.knowledge.ike2 import resolver

    ri = resolver.resolve("E910", None)
    ci = to_compliance_input(ri, query_atom="E910")
    result = evaluate(
        [ci],
        SimpleNamespace(restrictions={"vegan": "preference"}),
        rules_module.seeded_rules(),
    )
    assert to_external(result.verdict) == "UNCERTAIN"
    assert _effective_flags(ci).get("animal_origin") is not True


def test_stale_db_honey_insect_derived_cleared_by_tier1_overlay():
    """Live DB had honey insect_derived=true; overlay must clear it for Halal/Hindu."""
    stale = TruthAnchorFact(
        canonical_name="honey",
        flags={
            "animal_origin": True,
            "insect_derived": True,
            "bee_product": True,
        },
        knowledge_state="AUTO_CLASSIFIED",
    )
    ri = ResolvedIngredient(
        group=stale,
        source="db",
        confidence_band="high",
        trusted=True,
        resolution_layer="L3_db",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="honey")
    eff = _effective_flags(ci)
    assert eff.get("bee_product") is True
    assert eff.get("insect_derived") is not True
    rules = rules_module.seeded_rules()
    for restr, expect in (
        ("hindu_vegetarian", "SAFE"),
        ("halal", "SAFE"),
        ("kosher", "SAFE"),
        ("jain", "NOT_SAFE"),
        ("vegan", "NOT_SAFE"),
    ):
        got = to_external(
            evaluate([ci], SimpleNamespace(restrictions={restr: "medical"}), rules).verdict
        )
        assert got == expect, (restr, got)


def test_discovered_ks_elevated_when_tier1_locked_exists():
    """Systemic: DISCOVERED DB rows for Tier-1 LOCKED canons must still Avoid."""
    disc = TruthAnchorFact(
        canonical_name="tuna",
        flags={"animal_origin": True, "fish_source": True, "animal_species": "fish"},
        knowledge_state="DISCOVERED",
    )
    ri = ResolvedIngredient(
        group=disc,
        source="db",
        confidence_band="high",
        trusted=True,
        resolution_layer="L3_db",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="tuna")
    rules = rules_module.seeded_rules()
    profile = SimpleNamespace(restrictions={"fish_allergy": "medical"})
    assert to_external(evaluate([ci], profile, rules).verdict) == "NOT_SAFE"


def test_discovered_ks_still_blocks_when_no_tier1():
    """Without Tier-1 curation, DISCOVERED must not firm-Avoid medical allergies."""
    disc = TruthAnchorFact(
        canonical_name="zzzx_discovered_fish_oil_analogue",
        flags={"animal_origin": True, "fish_source": True},
        knowledge_state="DISCOVERED",
    )
    ri = ResolvedIngredient(
        group=disc,
        source="db",
        confidence_band="high",
        trusted=True,
        resolution_layer="L3_db",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom="zzzx_discovered_fish_oil_analogue")
    rules = rules_module.seeded_rules()
    profile = SimpleNamespace(restrictions={"fish_allergy": "medical"})
    assert to_external(evaluate([ci], profile, rules).verdict) == "UNCERTAIN"
