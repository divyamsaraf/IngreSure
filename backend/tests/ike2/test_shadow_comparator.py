from types import SimpleNamespace

from core.knowledge.ike2.shadow.comparator import compare


def test_match_when_equal():
    row = compare(legacy_verdict="SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["match"] is True
    assert row["false_safe_regression"] is False


def test_compare_agreement_no_regression():
    diff = compare("NOT_SAFE", "NOT_SAFE", "gelatin")
    assert diff["match"] is True
    assert diff["false_safe_regression"] is False


def test_legacy_uncertain_ike2_safe_without_flags_is_not_regression():
    """Legacy UNCERTAIN is not ground truth — do not flag without rule context."""
    diff = compare("UNCERTAIN", "SAFE", "wheat gluten", restriction_ids=["vegan"])
    assert diff["match"] is False
    assert diff["false_safe_regression"] is False


def test_legacy_not_safe_ike2_safe_without_matching_flags_is_not_regression():
    diff = compare("NOT_SAFE", "SAFE", "mystery")
    assert diff["false_safe_regression"] is False


def test_false_safe_when_ike2_safe_but_allergen_rule_matches_flags():
    peanut_rule = SimpleNamespace(
        restriction="peanut_allergy",
        kind="flag",
        trigger_flag="peanut_source",
        match_value=True,
        action="FAIL",
        min_knowledge_state="AUTO_CLASSIFIED",
    )
    diff = compare(
        "NOT_SAFE",
        "SAFE",
        "peanut",
        restriction_ids=["peanut_allergy"],
        ingredient_flags=[{"peanut_source": True}],
        rules=[peanut_rule],
    )
    assert diff["false_safe_regression"] is True


def test_vegan_safe_with_gluten_flags_is_not_regression():
    """Gluten flags must not fire vegan's animal_origin rule."""
    vegan_rule = SimpleNamespace(
        restriction="vegan",
        kind="flag",
        trigger_flag="animal_origin",
        match_value=True,
        action="FAIL",
        min_knowledge_state="DISCOVERED",
    )
    gluten_rule = SimpleNamespace(
        restriction="gluten_free",
        kind="flag",
        trigger_flag="gluten_source",
        match_value=True,
        action="FAIL",
        min_knowledge_state="AUTO_CLASSIFIED",
    )
    diff = compare(
        "UNCERTAIN",
        "SAFE",
        "wheat gluten",
        restriction_ids=["vegan"],
        ingredient_flags=[{"gluten_source": True, "animal_origin": False}],
        rules=[vegan_rule, gluten_rule],
    )
    assert diff["false_safe_regression"] is False


def test_gluten_free_safe_with_gluten_flags_is_regression():
    gluten_rule = SimpleNamespace(
        restriction="gluten_free",
        kind="flag",
        trigger_flag="gluten_source",
        match_value=True,
        action="FAIL",
        min_knowledge_state="AUTO_CLASSIFIED",
    )
    diff = compare(
        "UNCERTAIN",
        "SAFE",
        "wheat gluten",
        restriction_ids=["gluten_free"],
        ingredient_flags=[{"gluten_source": True}],
        rules=[gluten_rule],
    )
    assert diff["false_safe_regression"] is True


def test_compare_includes_restriction_ids_in_payload():
    diff = compare("SAFE", "SAFE", "water", restriction_ids=["vegan", "gluten_free"])
    assert diff["restriction_ids"] == ["vegan", "gluten_free"]
