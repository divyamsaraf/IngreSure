from core.knowledge.ike2.shadow.comparator import compare


def test_flags_false_safe_regression():
    row = compare(legacy_verdict="NOT_SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["false_safe_regression"] is True


def test_match_when_equal():
    row = compare(legacy_verdict="SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["match"] is True
    assert row["false_safe_regression"] is False


def test_compare_agreement_no_regression():
    diff = compare("NOT_SAFE", "NOT_SAFE", "gelatin")
    assert diff["match"] is True
    assert diff["false_safe_regression"] is False


def test_compare_false_safe_when_primary_safe_legacy_worse():
    # primary (ike2) SAFE, legacy NOT_SAFE -> regression
    diff = compare("NOT_SAFE", "SAFE", "mystery")
    assert diff["false_safe_regression"] is True
