"""Bulk ETL sources never firm-SAFE: absence of a flag is not evidence."""
from types import SimpleNamespace

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import to_external
from core.ontology.ingredient_schema import Ingredient


def _group(source: str, uncertainty_flags=None):
    return SimpleNamespace(
        source=source,
        uncertainty_flags=list(uncertainty_flags or []),
        canonical_name="bulk clean row",
    )


def test_usda_infoods_ifct_fssai_never_trusted_even_without_markers():
    for src in ("usda", "infoods", "ifct", "fssai", "usda_fdc"):
        assert is_trusted_for_compliance(_group(src), "db", "high") is False, src


def test_bulk_classification_method_caps_when_source_column_missing():
    """Alias view historically omitted source; bulk:<src> still caps SAFE."""
    g = SimpleNamespace(
        uncertainty_flags=[],
        classification_method="bulk:fssai",
        canonical_name="bread and acesulfame",
    )
    assert is_trusted_for_compliance(g, "db", "high") is False


def test_ontology_static_still_trusted():
    ing = Ingredient(id="o", canonical_name="salt", uncertainty_flags=[])
    assert is_trusted_for_compliance(ing, "static", "high") is True


def test_usda_clean_pass_never_firm_safe():
    """USDA group with no true allergen flags must not return firm SAFE."""
    trusted = is_trusted_for_compliance(_group("usda"), "db", "high")
    ci = ComplianceInput(
        canonical_name="Bread, egg",
        flags={"uncertainty_flags": []},
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
            SimpleNamespace(restrictions={"gluten_free": "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )
    assert v != "SAFE"
    assert trusted is False
