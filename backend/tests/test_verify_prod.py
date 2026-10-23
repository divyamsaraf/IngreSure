from scripts.verify_prod import EXPECTED_RULES, VIEW, required_view_columns, summarize


def test_expected_rule_count_is_58():
    assert EXPECTED_RULES == 58
    assert VIEW == "ike2_v_alias_resolution"
    cols = required_view_columns()
    assert "source" in cols
    assert "asserted_flags" in cols


def test_summarize_fails_on_rule_mismatch():
    report = {
        "rules": 52,
        "view_columns": ["source", "asserted_flags"],
        "flags_null": 0,
        "missing_objects": [],
        "applied_migrations": ["20261014000000"],
    }
    ok, failures = summarize(report)
    assert ok is False
    assert any("58" in f for f in failures)
