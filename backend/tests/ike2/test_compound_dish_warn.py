"""Compound dishes have unknown composition — never invent dairy/egg Avoid or firm Safe."""
from __future__ import annotations

from types import SimpleNamespace

from core.knowledge.ike2 import compliance as compliance_module
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.resolution_cache import clear as clear_resolution_cache
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores.local_ontology import reset_cache as reset_local_ontology
from core.knowledge.ike2.verdict import Verdict, to_external


def setup_function():
    clear_resolution_cache()
    reset_local_ontology()


def test_affogato_warn_no_invented_dairy_or_egg():
    r = resolve("affogato", None)
    assert r.status == "resolved" and r.trusted
    assert r.resolution_layer == "L1_truth_anchor"
    inp = to_compliance_input(r, query_atom="affogato")
    assert inp.verdict_cap == "WARN"
    assert inp.flags.get("dairy_source") is not True
    assert inp.flags.get("egg_source") is not True
    rules = rules_module.seeded_rules()
    for restriction in ("vegan", "egg_free", "dairy_free"):
        profile = SimpleNamespace(restrictions={restriction: "medical"})
        result = compliance_module.evaluate([inp], profile, rules)
        assert result.verdict != Verdict.SAFE, restriction
        assert result.verdict != Verdict.FAIL, restriction
        assert to_external(result.verdict) == "UNCERTAIN", restriction


def test_prepared_coffee_desserts_are_warn_compounds():
    for raw in ("souffle", "ice cream sandwich", "latte", "veggie burger", "tiramisu"):
        r = resolve(raw, None)
        assert r.status == "resolved", raw
        assert r.resolution_layer == "L1_truth_anchor", raw
        inp = to_compliance_input(r, query_atom=raw)
        assert inp.verdict_cap == "WARN", raw
