"""NULL/missing group provenance must never firm-SAFE (fail-closed)."""
from types import SimpleNamespace

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import to_external


def test_null_source_on_db_channel_is_untrusted():
    g = SimpleNamespace(source=None, uncertainty_flags=[], canonical_name="mystery")
    assert is_trusted_for_compliance(g, "db", "high") is False


def test_missing_source_attr_on_db_channel_is_untrusted():
    g = SimpleNamespace(uncertainty_flags=[], canonical_name="mystery")
    assert is_trusted_for_compliance(g, "db", "high") is False


def test_empty_source_string_is_untrusted():
    g = SimpleNamespace(source="", uncertainty_flags=[], canonical_name="mystery")
    assert is_trusted_for_compliance(g, "db", "high") is False


def test_unknown_source_label_is_untrusted():
    g = SimpleNamespace(source="some_new_etl", uncertainty_flags=[], canonical_name="x")
    assert is_trusted_for_compliance(g, "db", "high") is False


def test_ontology_source_still_trusted_on_db_channel():
    g = SimpleNamespace(source="ontology", uncertainty_flags=[], canonical_name="salt")
    assert is_trusted_for_compliance(g, "db", "high") is True


def test_null_source_never_firm_safe():
    trusted = is_trusted_for_compliance(
        SimpleNamespace(source=None, uncertainty_flags=[]), "db", "high"
    )
    ci = ComplianceInput(
        canonical_name="mystery bulk row",
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
    assert trusted is False
    assert v != "SAFE"
