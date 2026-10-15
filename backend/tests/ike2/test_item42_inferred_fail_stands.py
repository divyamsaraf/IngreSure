"""Item 42: triggered allergy/medical FAIL stands despite *_inferred untrusted.

*_inferred (and untrusted generally) still caps a clean pass below SAFE.
"""
from types import SimpleNamespace

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict, to_external


def _ci(**overrides) -> ComplianceInput:
    base = dict(
        canonical_name="__test_item42__",
        flags={},
        knowledge_state="AUTO_CLASSIFIED",
        trusted=False,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
        may_contain=False,
    )
    base.update(overrides)
    return ComplianceInput(**base)


def _eval(ci, restriction: str):
    return evaluate(
        [ci],
        SimpleNamespace(restrictions={restriction: "medical"}),
        rules_module.seeded_rules(),
    )


def test_triggered_fish_allergy_fail_stands_when_untrusted_inferred():
    ci = _ci(
        flags={
            "fish_source": True,
            "animal_origin": True,
            "uncertainty_flags": ["usda_fdc_bulk_inferred"],
        },
        trusted=False,
    )
    assert to_external(_eval(ci, "fish_allergy").verdict) == "NOT_SAFE"


def test_triggered_dairy_free_fail_stands_when_untrusted_inferred():
    ci = _ci(
        flags={
            "dairy_source": True,
            "animal_origin": True,
            "uncertainty_flags": ["usda_fdc_name_inferred"],
        },
        trusted=False,
    )
    assert to_external(_eval(ci, "dairy_free").verdict) == "NOT_SAFE"


def test_clean_pass_with_inferred_still_caps_uncertain():
    ci = _ci(
        flags={"uncertainty_flags": ["usda_fdc_bulk_inferred"]},
        trusted=False,
    )
    assert _eval(ci, "fish_allergy").verdict == Verdict.UNCERTAIN
    assert to_external(_eval(ci, "fish_allergy").verdict) == "UNCERTAIN"


def test_untrusted_vegan_triggered_still_uncertain():
    """Lifestyle stays fail-closed under untrusted — allergy/medical only stands."""
    ci = _ci(
        flags={
            "animal_origin": True,
            "uncertainty_flags": ["infoods_anfood_inferred"],
        },
        trusted=False,
    )
    assert to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"vegan": "preference"}),
            rules_module.seeded_rules(),
        ).verdict
    ) == "UNCERTAIN"


def test_untrusted_halal_kosher_jain_animal_origin_stay_uncertain():
    """Religious diets match vegan: inferred + animal_origin → UNCERTAIN, not Avoid."""
    ci = _ci(
        flags={
            "animal_origin": True,
            "uncertainty_flags": ["usda_fdc_name_inferred"],
        },
        trusted=False,
    )
    for rid in ("halal", "kosher", "jain"):
        assert to_external(
            evaluate(
                [ci],
                SimpleNamespace(restrictions={rid: "preference"}),
                rules_module.seeded_rules(),
            ).verdict
        ) == "UNCERTAIN", rid
