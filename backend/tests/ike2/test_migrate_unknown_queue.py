"""Item 18 step 3: legacy unknown_ingredients -> ike2_unknown_queue plan."""
from __future__ import annotations

from core.knowledge.ike2.unknown_queue import plan_legacy_migration

# Live local rows as of 2026-09-23.
LEGACY = [
    {"normalized_key": "wheat flour", "frequency": 32, "resolved": False, "resolution_attempts": 0,
     "raw_inputs": ["Wheat Flour"]},
    {"normalized_key": "a", "frequency": 32, "resolved": False, "resolution_attempts": 0},
    {"normalized_key": "zyzzx unknown starch q99", "frequency": 16, "resolved": False, "resolution_attempts": 0},
    {"normalized_key": "b", "frequency": 16, "resolved": False, "resolution_attempts": 0},
]


def _by_op(ops, op):
    return [o for o in ops if o["op"] == op]


def test_only_wheat_flour_carries_over_with_frequency():
    ops = plan_legacy_migration(LEGACY, existing={})
    [ins] = _by_op(ops, "insert")
    assert ins["key"] == "wheat flour"
    assert ins["row"]["frequency"] == 32
    assert ins["row"]["status"] == "pending"
    assert ins["row"]["enrichment"]["raw_inputs"] == ["Wheat Flour"]
    assert ins["row"]["enrichment"]["migrated_from"] == "unknown_ingredients"
    assert {o["key"] for o in _by_op(ops, "skip")} == {"a", "b", "zyzzx unknown starch q99"}
    assert all(o["reason"] == "junk" for o in _by_op(ops, "skip"))


def test_resolved_legacy_rows_are_skipped():
    ops = plan_legacy_migration([{**LEGACY[0], "resolved": True}], existing={})
    assert ops == [{"op": "skip", "key": "wheat flour", "reason": "resolved"}]


def test_rerun_is_idempotent():
    first = plan_legacy_migration(LEGACY, existing={})
    existing = {"wheat flour": {"id": "q1", **_by_op(first, "insert")[0]["row"]}}
    again = plan_legacy_migration(LEGACY, existing=existing)
    assert _by_op(again, "insert") == []
    assert _by_op(again, "update") == []


def test_conflict_keeps_max_frequency_never_sums():
    live_lower = {"wheat flour": {"id": "q1", "frequency": 5, "enrichment": {"raw_inputs": ["wheat flour"]}}}
    [upd] = _by_op(plan_legacy_migration(LEGACY, live_lower), "update")
    assert upd["row"]["frequency"] == 32
    assert upd["row"]["enrichment"]["raw_inputs"] == ["wheat flour", "Wheat Flour"]

    live_higher = {"wheat flour": {"id": "q1", "frequency": 50, "enrichment": {}}}
    [upd] = _by_op(plan_legacy_migration(LEGACY, live_higher), "update")
    assert upd["row"]["frequency"] == 50
