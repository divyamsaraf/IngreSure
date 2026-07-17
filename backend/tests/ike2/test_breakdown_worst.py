from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict
from core.knowledge.ike2 import rules


def _inp(name, **flags):
    return SimpleNamespace(
        canonical_name=name, flags=flags, knowledge_state="LOCKED",
        trusted=True, alcohol_role=None, verdict_cap=flags.get("verdict_cap"),
        trace=False, may_contain=False,
    )


def test_hindu_veg_gelatin_breakdown_keeps_fail_not_last_safe():
    gel = _inp("gelatin", animal_origin=True, fish_source=True,
               animal_species="bovine/porcine/fish depending on source",
               uncertainty_flags=["source_species_unspecified_on_label"],
               verdict_cap="WARN")
    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "medical"})
    result = evaluate([gel], profile, rules.seeded_rules())
    assert result.breakdown[("gelatin", "hindu_vegetarian")] == Verdict.FAIL
