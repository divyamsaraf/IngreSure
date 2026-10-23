"""Unknown / empty audit status must fail closed to UNCERTAIN, never SAFE."""
from core.knowledge.ike2.verdict import Verdict, to_external
from core.models.verdict import normalize_external_status, worst_external_status
from scripts.run_input_cases import _verdict_status


def test_unknown_status_is_not_safe():
    for raw in (None, "", "UNKNOWN", "unknown", "CHECK", "WARN", "DEPENDS", "GARBAGE"):
        assert normalize_external_status(raw) == "UNCERTAIN"
        assert normalize_external_status(raw) != "SAFE"


def test_avoid_and_fail_map_to_not_safe():
    assert normalize_external_status("AVOID") == "NOT_SAFE"
    assert normalize_external_status("avoid") == "NOT_SAFE"
    assert normalize_external_status("NOT_SAFE") == "NOT_SAFE"
    assert normalize_external_status("FAIL") == "NOT_SAFE"


def test_worst_starts_uncertain_not_safe():
    assert worst_external_status([]) == "UNCERTAIN"
    assert worst_external_status([""]) == "UNCERTAIN"
    assert worst_external_status(["UNKNOWN"]) == "UNCERTAIN"
    assert worst_external_status(["CHECK", "WARN"]) == "UNCERTAIN"
    assert worst_external_status(["SAFE", "UNKNOWN"]) == "UNCERTAIN"
    assert worst_external_status(["SAFE"]) == "SAFE"
    assert worst_external_status(["SAFE", "AVOID"]) == "NOT_SAFE"


def test_unknown_ike2_enum_is_uncertain_not_safe():
    assert to_external(object()) == "UNCERTAIN"
    assert to_external(99) == "UNCERTAIN"
    assert to_external(Verdict.WARN) == "UNCERTAIN"
    assert to_external(Verdict.SAFE) == "SAFE"


def test_harness_unknown_group_status_is_not_safe():
    assert _verdict_status({"groups": [{"status": "UNKNOWN"}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{"status": ""}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{"status": "CHECK"}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{"status": "WARN"}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{"status": "DEPENDS"}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{}]}) == "UNCERTAIN"
    assert _verdict_status({"groups": [{"status": "SAFE"}]}) == "SAFE"
    assert _verdict_status({"groups": [{"status": "avoid"}]}) == "NOT_SAFE"
    assert _verdict_status({"verdict": {"status": "UNKNOWN"}}) == "UNCERTAIN"
    assert _verdict_status({"verdict": {"status": "SAFE"}}) == "SAFE"
