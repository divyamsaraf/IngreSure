"""Shared hazard lexicon: false friends, negation, atom derive agreement."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.parsing.hazard_lexicon import hazard_hits_in_text


def test_false_friends_do_not_fire_dairy():
    for text in (
        "beurre de cacao",
        "cocoa butter",
        "kakaobutter",
        "lait de coco",
        "leche de coco",
        "kokosmilch",
        "lait d'amande",
        "mandelmilch",
        "milk thistle",
        "milk thistle seed",
        "tofu yogurt",
        "soy yoghurt",
        "coconut yogurt",
    ):
        assert "dairy" not in hazard_hits_in_text(text), text
        assert not derive_identity_flags(text).get("dairy_source"), text


def test_tofu_yogurt_does_not_dual_origin_pollute():
    """Regression: lexicon dairy on tofu yogurt broke ontology inject (CI)."""
    flags = derive_identity_flags("tofu yogurt", {"plant_origin": True})
    assert flags.get("dairy_source") is not True
    assert flags.get("animal_origin") is not True


def test_negation_masks_soya_free_and_no_soy():
    for text in (
        "allergen advice: dairy free, gluten free, soya free, vegan",
        "NO SOY GLUTEN FREE NO DAIRY",
        "sans soja, sans gluten",
        "ohne soya",
        "sin soja",
    ):
        assert "soy" not in hazard_hits_in_text(text), text


def test_real_dairy_and_soy_still_hit():
    assert "dairy" in hazard_hits_in_text("poudre de lait entier")
    assert "dairy" in hazard_hits_in_text("beurre")
    assert "soy" in hazard_hits_in_text("soy lecithin")
    assert "gluten" in hazard_hits_in_text("farine de blé")


def test_french_lait_atom_is_not_safe_for_dairy_free():
    """Lexicon + derive make FR dairy atoms Avoid, not L5-only sweep rescue."""
    cache.clear()
    rules = rules_module.seeded_rules()
    atom = "lait"
    ci = to_compliance_input(resolve(atom, None), query_atom=atom)
    assert ci.flags.get("dairy_source") is True
    assert ci.trusted is True
    v = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"dairy_free": "medical"}),
            rules,
        ).verdict
    )
    assert v == "NOT_SAFE"
