from core.knowledge.ike2.shadow.comparator import compare


def test_flags_false_safe_regression():
    row = compare(legacy_verdict="NOT_SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["false_safe_regression"] is True


def test_match_when_equal():
    row = compare(legacy_verdict="SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["match"] is True
    assert row["false_safe_regression"] is False
