"""Resolution-cache seed must not let a lower-trust catalog row hide a LOCKED anchor."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2 import truth_anchor
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict


def _seed():
    cache.clear()
    cache.seed_tier1()


def test_locked_anchor_overwrites_lower_trust_catalog_row():
    _seed()
    gelatin = cache.get(cache.cache_key("gelatin", None)).group
    assert gelatin.knowledge_state == "LOCKED"
    assert gelatin.flags["animal_origin"] is True
    assert gelatin.flags["fish_source"] is True

    inosinate = cache.get(cache.cache_key("disodium inosinate", None)).group
    assert inosinate.knowledge_state == "LOCKED"
    assert inosinate.flags["animal_origin"] is True
    # Catalog origin caution is kept; the hand one-liner has no recorded reason to drop it.
    assert "may_be_from_yeast_or_tapioca" in inosinate.flags["uncertainty_flags"]
    assert inosinate.flags.get("verdict_cap") == "WARN"
    hand = truth_anchor.lookup("disodium inosinate")
    assert not hand.flags.get("verdict_cap")
    assert "may_be_from_yeast_or_tapioca" not in (hand.flags.get("uncertainty_flags") or [])


def test_lookup_still_returns_the_unmerged_catalog_row_for_e_codes():
    """Cache merge must not mutate the catalog objects lookup() returns."""
    _seed()
    e542 = truth_anchor.lookup("e542")
    assert e542.knowledge_state == "AUTO_CLASSIFIED"
    assert not e542.flags.get("animal_origin")


def test_bone_phosphate_keeps_animal_origin_and_synthetic_uncertainty():
    _seed()
    fact = cache.get(cache.cache_key("bone phosphate", None)).group
    assert fact.knowledge_state == "LOCKED"
    assert fact.flags["animal_origin"] is True
    assert "may_be_synthetic_tricalcium_phosphate" in fact.flags["uncertainty_flags"]
    assert fact.flags.get("verdict_cap") == "WARN"
    # Hand anchor itself stays as authored.
    hand = truth_anchor.lookup("bone phosphate")
    assert hand.knowledge_state == "LOCKED"
    assert "may_be_synthetic_tricalcium_phosphate" not in (hand.flags.get("uncertainty_flags") or [])


def test_disodium_inosinate_non_animal_diet_stays_warn_and_vegan_fails():
    """Peanut allergy does not trigger animal_origin. The catalog WARN cap
    must still block firm SAFE. Vegan still firm-FAILs on animal_origin.
    """
    cache.clear()
    resolved = resolve("disodium inosinate", None)
    ci = to_compliance_input(SimpleNamespace(group=resolved.group, trusted=True))
    rules = rules_module.seeded_rules()

    peanut = evaluate(
        [ci], SimpleNamespace(restrictions={"peanut_allergy": "medical"}), rules
    )
    assert peanut.verdict == Verdict.WARN
    assert peanut.verdict != Verdict.SAFE

    vegan = evaluate(
        [ci], SimpleNamespace(restrictions={"vegan": "preference"}), rules
    )
    assert vegan.verdict == Verdict.FAIL


def test_bone_phosphate_vegan_is_firm_fail():
    cache.clear()
    resolved = resolve("bone phosphate", None)
    ci = to_compliance_input(SimpleNamespace(group=resolved.group, trusted=True))
    profile = SimpleNamespace(restrictions={"vegan": "preference"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert result.verdict == Verdict.FAIL

    e542 = resolve("e542", None)
    assert e542.group.flags["animal_origin"] is True
    assert "may_be_synthetic_tricalcium_phosphate" in e542.group.flags["uncertainty_flags"]
