"""Spec harness must not start worst at SAFE (remaining fail-open hole)."""
from pathlib import Path

from core.models.verdict import worst_external_status
from scripts.run_input_cases import _verdict_status


def test_source_has_no_worst_safe_default():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "run_input_cases.py").read_text(
        encoding="utf-8"
    )
    assert 'worst = "SAFE"' not in src
    assert "worst_external_status" in src


def test_empty_groups_do_not_become_safe():
    assert _verdict_status({"groups": []}) is None
    assert _verdict_status({"groups": [{"status": "SAFE"}, {"status": "NOT_SAFE"}]}) == "NOT_SAFE"
    assert _verdict_status({"verdict": {"status": "depends"}}) == "UNCERTAIN"


def test_worst_empty_fold_is_uncertain():
    assert worst_external_status([]) == "UNCERTAIN"
