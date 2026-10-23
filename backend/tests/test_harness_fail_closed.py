"""Spec harness must not start worst at SAFE (remaining fail-open hole)."""
from pathlib import Path

import pytest

from core.models.verdict import normalize_external_status, worst_external_status
from scripts.run_input_cases import _verdict_status


def _broken_worst_safe_default(statuses) -> str:
    """The fail-open hole: empty fold stays SAFE."""
    worst = "SAFE"
    rank = {"NOT_SAFE": 3, "UNCERTAIN": 2, "SAFE": 1}
    for raw in statuses or []:
        mapped = normalize_external_status(raw)
        if rank[mapped] > rank[worst]:
            worst = mapped
    return worst


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


def test_broken_worst_safe_default_fails_the_gate():
    assert _broken_worst_safe_default([]) == "SAFE"
    assert worst_external_status([]) == "UNCERTAIN"
    with pytest.raises(AssertionError):
        assert _broken_worst_safe_default([]) != "SAFE"
    with pytest.raises(AssertionError):
        assert _broken_worst_safe_default([]) == "UNCERTAIN"
