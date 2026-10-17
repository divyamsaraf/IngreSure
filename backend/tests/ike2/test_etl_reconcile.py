from types import SimpleNamespace

from core.knowledge.ike2.etl.reconcile import reconcile


def _group(
    dairy_source=False,
    gluten_source=False,
    knowledge_state="AUTO_CLASSIFIED",
    source="usda",
    asserted_flags=None,
):
    return SimpleNamespace(
        dairy_source=dairy_source,
        gluten_source=gluten_source,
        knowledge_state=knowledge_state,
        source=source,
        asserted_flags=list(asserted_flags or []),
    )


def test_unset_false_to_true_no_demotion():
    """Default false is not a verified negative — adopt true, do not demote."""
    existing = _group(dairy_source=False, knowledge_state="AUTO_CLASSIFIED", source="usda")
    res = reconcile(
        existing,
        {"dairy_source": True},
        incoming_source="openfoodfacts",
        incoming_asserted=["dairy_source"],
    )
    assert res.merged_flags["dairy_source"] is True
    assert res.needs_review is False
    assert res.knowledge_state == "AUTO_CLASSIFIED"
    assert "dairy_source" in res.merged_asserted_flags


def test_asserted_false_to_true_demotes():
    """Verified negative flipped by a new positive → demote."""
    existing = _group(
        dairy_source=False,
        knowledge_state="AUTO_CLASSIFIED",
        source="usda",
        asserted_flags=["dairy_source"],
    )
    res = reconcile(
        existing,
        {"dairy_source": True},
        incoming_source="openfoodfacts",
        incoming_asserted=["dairy_source"],
    )
    assert res.merged_flags["dairy_source"] is True
    assert res.needs_review is True
    assert res.knowledge_state == "DISCOVERED"
    assert "dairy_source" in res.merged_asserted_flags


def test_most_restrictive_ors_without_asserted_still_keeps_true():
    existing = _group(dairy_source=True, knowledge_state="AUTO_CLASSIFIED", source="usda")
    res = reconcile(existing, {"dairy_source": False}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True
    assert res.needs_review is False


def test_lower_tier_cannot_override_verified_flags():
    existing = _group(dairy_source=True, knowledge_state="VERIFIED", source="human")
    res = reconcile(existing, {"dairy_source": False}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True  # higher tier preserved


def test_locked_trust_survives_lower_tier_flag_addition():
    """Item 1 Prompt 2: protection keeps KS=LOCKED when provenance source is set."""
    existing = _group(
        dairy_source=True,
        gluten_source=False,
        knowledge_state="LOCKED",
        source="e_number_catalog",
    )
    res = reconcile(
        existing,
        {"dairy_source": True, "gluten_source": True},
        incoming_source="openfoodfacts",
    )
    assert res.merged_flags["gluten_source"] is False  # frozen — lower tier cannot add
    assert res.merged_flags["dairy_source"] is True
    assert res.knowledge_state == "LOCKED"
    assert res.needs_review is False


def test_locked_without_provenance_unasserted_add_no_demotion():
    """Sourceless LOCKED + unasserted false→true: adopt, no demotion (marker gate)."""
    existing = SimpleNamespace(
        dairy_source=False,
        gluten_source=False,
        knowledge_state="LOCKED",
        # no source attr — unprotected
    )
    res = reconcile(
        existing,
        {"dairy_source": False, "gluten_source": True},
        incoming_source="openfoodfacts",
        incoming_asserted=["gluten_source"],
    )
    assert res.merged_flags["gluten_source"] is True
    assert res.needs_review is False
    assert res.knowledge_state == "LOCKED"


def test_locked_without_provenance_asserted_add_demotes():
    existing = SimpleNamespace(
        dairy_source=False,
        gluten_source=False,
        knowledge_state="LOCKED",
        asserted_flags=["gluten_source"],
    )
    res = reconcile(
        existing,
        {"gluten_source": True},
        incoming_source="openfoodfacts",
        incoming_asserted=["gluten_source"],
    )
    assert res.merged_flags["gluten_source"] is True
    assert res.needs_review is True
    assert res.knowledge_state == "DISCOVERED"


def test_non_locked_unasserted_ors_without_demotion():
    existing = _group(
        dairy_source=False,
        gluten_source=False,
        knowledge_state="AUTO_CLASSIFIED",
        source="usda",
    )
    res = reconcile(
        existing,
        {"gluten_source": True},
        incoming_source="openfoodfacts",
        incoming_asserted=["gluten_source"],
    )
    assert res.merged_flags["gluten_source"] is True
    assert res.needs_review is False
    assert res.knowledge_state == "AUTO_CLASSIFIED"


def test_merged_asserted_unions_existing_and_incoming():
    existing = _group(
        dairy_source=True,
        asserted_flags=["dairy_source"],
    )
    res = reconcile(
        existing,
        {"gluten_source": True},
        incoming_source="usda",
        incoming_asserted=["gluten_source"],
    )
    assert res.merged_asserted_flags == ["dairy_source", "gluten_source"]


def test_equal_tier_asserted_false_clears_sticky_or():
    existing = SimpleNamespace(
        synthetic=True,
        knowledge_state="DISCOVERED",
        source="fssai",
        asserted_flags=["synthetic"],
    )
    res = reconcile(
        existing,
        {"synthetic": False},
        incoming_source="ontology",
        incoming_asserted=["synthetic"],
        incoming_knowledge_state="AUTO_CLASSIFIED",
    )
    assert res.merged_flags["synthetic"] is False
    assert res.needs_review is False
    assert res.knowledge_state == "AUTO_CLASSIFIED"
    assert "synthetic" in res.merged_asserted_flags


def test_lower_tier_asserted_false_cannot_clear():
    existing = SimpleNamespace(
        synthetic=True,
        knowledge_state="AUTO_CLASSIFIED",
        source="ontology",
        asserted_flags=["synthetic"],
    )
    res = reconcile(
        existing,
        {"synthetic": False},
        incoming_source="openfoodfacts",
        incoming_asserted=["synthetic"],
        incoming_knowledge_state="AUTO_CLASSIFIED",
    )
    assert res.merged_flags["synthetic"] is True
    assert res.knowledge_state == "AUTO_CLASSIFIED"


def test_repromote_discovered_when_no_conflict():
    existing = _group(
        dairy_source=True,
        knowledge_state="DISCOVERED",
        source="usda",
        asserted_flags=["dairy_source"],
    )
    res = reconcile(
        existing,
        {"dairy_source": True},
        incoming_source="usda",
        incoming_asserted=["dairy_source"],
        incoming_knowledge_state="AUTO_CLASSIFIED",
    )
    assert res.needs_review is False
    assert res.knowledge_state == "AUTO_CLASSIFIED"
