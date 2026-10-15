"""l-cysteine, cysteine, E920, and E910 are one substance and one verdict."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict


_LABELS = ("l-cysteine", "cysteine", "E920", "E910")


def _vegan(label: str) -> Verdict:
    cache.clear()
    resolved = resolve(label, None)
    ci = to_compliance_input(resolved, query_atom=label)
    result = evaluate(
        [ci],
        SimpleNamespace(restrictions={"vegan": "preference"}),
        rules_module.seeded_rules(),
    )
    return result.verdict


def test_cysteine_labels_share_one_vegan_verdict():
    from core.knowledge.ike2.truth_anchor import lookup

    hand = lookup("l-cysteine")
    assert hand.flags.get("animal_origin") is not True
    assert hand.flags.get("verdict_cap") == "WARN"
    assert "may_be_synthetic_or_from_plant_fermentation" in hand.flags["uncertainty_flags"]
    assert "traditionally_from_poultry_feathers_or_hog_hair" in hand.flags["uncertainty_flags"]

    verdicts = {label: _vegan(label) for label in _LABELS}
    assert len(set(verdicts.values())) == 1, verdicts
    assert verdicts["l-cysteine"] == Verdict.WARN
    assert verdicts["l-cysteine"] != Verdict.FAIL
