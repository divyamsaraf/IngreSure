"""Item 42: category_derived must not lift the group-level SAFE ceiling.

Category evidence supports fish/shellfish positives; it does not certify the
absence of gluten/egg/dairy on breaded/battered/creamed rows. Positives may
stand when untrusted; clean passes stay capped.
"""
from types import SimpleNamespace

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import to_external
from core.ontology.ingredient_schema import Ingredient


def _ing(uncertainty_flags):
    return Ingredient(
        id="t",
        canonical_name="shrimp breaded",
        uncertainty_flags=list(uncertainty_flags),
    )


def test_category_derived_alone_is_untrusted_for_db():
    assert is_trusted_for_compliance(
        _ing(["usda_fdc_category_derived"]), "db", "high"
    ) is False


def test_category_derived_plus_inferred_still_untrusted():
    assert is_trusted_for_compliance(
        _ing(["usda_fdc_category_derived", "usda_fdc_name_inferred"]),
        "db",
        "high",
    ) is False


def test_breaded_fish_shellfish_never_safe_under_gluten_egg_dairy():
    """Trusted fish/shellfish group with a breaded name must not firm-SAFE
    under gluten_free / egg_free / dairy_free when evidence is category-only.
    """
    for restriction in ("gluten_free", "egg_free", "dairy_free"):
        # Simulate trust derived from category_derived (must be False after fix).
        trusted = is_trusted_for_compliance(
            _ing(["usda_fdc_category_derived"]), "db", "high"
        )
        ci = ComplianceInput(
            canonical_name="Crustaceans, shrimp, breaded, frozen",
            flags={
                "shellfish_source": True,
                "animal_origin": True,
                "gluten_source": False,
                "egg_source": False,
                "dairy_source": False,
                "uncertainty_flags": ["usda_fdc_category_derived"],
            },
            knowledge_state="AUTO_CLASSIFIED",
            trusted=trusted,
            alcohol_role="none",
            verdict_cap=None,
            trace=False,
            may_contain=False,
        )
        v = to_external(
            evaluate(
                [ci],
                SimpleNamespace(restrictions={restriction: "medical"}),
                rules_module.seeded_rules(),
            ).verdict
        )
        assert v != "SAFE", (restriction, v, trusted)


def test_fish_allergy_fail_still_stands_with_category_derived_untrusted():
    trusted = is_trusted_for_compliance(
        _ing(["usda_fdc_category_derived"]), "db", "high"
    )
    ci = ComplianceInput(
        canonical_name="Fish, cod, Atlantic, raw",
        flags={
            "fish_source": True,
            "animal_origin": True,
            "uncertainty_flags": ["usda_fdc_category_derived"],
        },
        knowledge_state="AUTO_CLASSIFIED",
        trusted=trusted,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
        may_contain=False,
    )
    assert to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"fish_allergy": "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    ) == "NOT_SAFE"
