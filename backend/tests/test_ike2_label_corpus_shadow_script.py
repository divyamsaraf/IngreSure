"""False-Safe hard gate: scripts/ike2_label_corpus_shadow.py must fail on any
false_safe_regression unconditionally, regardless of --fail-below-threshold.
"""
from __future__ import annotations

from unittest.mock import patch

from scripts.ike2_label_corpus_shadow import main


def _report(*, match_rate=1.0, false_safe_regressions=None, passed=True):
    false_safe_regressions = false_safe_regressions or []
    return {
        "total": 10,
        "matches": int(match_rate * 10),
        "match_rate": match_rate,
        "false_safe_regressions": false_safe_regressions,
        "mismatches": [],
        "threshold": 0.85,
        "passed": passed,
    }


def test_fails_on_false_safe_even_without_fail_below_threshold_flag():
    bad = _report(
        false_safe_regressions=[
            {"id": "x1", "legacy_verdict": "NOT_SAFE", "ike2_verdict": "SAFE", "raw_input": "peanut"}
        ],
        passed=False,
    )
    with patch("scripts.ike2_label_corpus_shadow.run_shadow_report", return_value=bad):
        assert main([]) == 1


def test_fails_on_false_safe_with_fail_below_threshold_flag():
    bad = _report(
        false_safe_regressions=[
            {"id": "x1", "legacy_verdict": "NOT_SAFE", "ike2_verdict": "SAFE", "raw_input": "peanut"}
        ],
        passed=False,
    )
    with patch("scripts.ike2_label_corpus_shadow.run_shadow_report", return_value=bad):
        assert main(["--fail-below-threshold"]) == 1


def test_passes_when_no_false_safe_and_no_flag():
    good = _report(match_rate=0.5, passed=False)  # below threshold, but flag absent
    with patch("scripts.ike2_label_corpus_shadow.run_shadow_report", return_value=good):
        assert main([]) == 0


def test_fails_below_threshold_only_when_flag_set_and_no_false_safe():
    below = _report(match_rate=0.5, passed=False)
    with patch("scripts.ike2_label_corpus_shadow.run_shadow_report", return_value=below):
        assert main(["--fail-below-threshold"]) == 1


def test_passes_when_matches_and_no_false_safe():
    good = _report(match_rate=1.0, passed=True)
    with patch("scripts.ike2_label_corpus_shadow.run_shadow_report", return_value=good):
        assert main(["--fail-below-threshold"]) == 0
