from types import SimpleNamespace

from core.knowledge.ike2.etl.reconcile import reconcile


def _group(dairy_source=False, knowledge_state="AUTO_CLASSIFIED", source="usda"):
    return SimpleNamespace(
        dairy_source=dairy_source,
        knowledge_state=knowledge_state,
        source=source,
    )


def test_conflict_takes_most_restrictive_and_flags_review():
    existing = _group(dairy_source=False, knowledge_state="AUTO_CLASSIFIED", source="usda")
    res = reconcile(existing, {"dairy_source": True}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True  # most restrictive wins
    assert res.needs_review is True
    assert res.knowledge_state in ("DISCOVERED", "UNCLASSIFIED")  # dropped


def test_lower_tier_cannot_override_verified():
    existing = _group(dairy_source=True, knowledge_state="VERIFIED", source="human")
    res = reconcile(existing, {"dairy_source": False}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True  # higher tier preserved
