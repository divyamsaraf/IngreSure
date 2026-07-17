import importlib
import time

import pytest

from core.bridge import map_ike2_to_compliance_verdict, run_new_engine_chat
from core.knowledge.ike2.compliance import ComplianceResult
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict, to_external
from core.models.verdict import VerdictStatus


def _reload_config(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("IKE2_MODE", raising=False)
    else:
        monkeypatch.setenv("IKE2_MODE", value)
    import core.config as config
    return importlib.reload(config)


@pytest.mark.parametrize("raw", [None, "", "off", "shadow", "fallback", "PRIMARY", "garbage"])
def test_ike2_mode_coerces_to_primary(monkeypatch, raw):
    cfg = _reload_config(monkeypatch, raw)
    assert cfg.IKE2_MODE == "primary"


def test_map_ike2_fail_to_not_safe():
    inputs = [
        ComplianceInput(
            canonical_name="gelatin",
            flags={"animal_origin": True},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        )
    ]
    result = ComplianceResult(
        Verdict.FAIL,
        matched_contains=["gelatin"],
        matched_may_contain=[],
        caution_reasons=["vegan:gelatin"],
        breakdown={("gelatin", "vegan"): Verdict.FAIL},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.status == VerdictStatus.NOT_SAFE
    assert v.status.value == to_external(Verdict.FAIL)
    assert "gelatin" in v.triggered_ingredients
    assert "vegan" in v.triggered_restrictions


def test_map_partial_unknown_status_from_to_external_only():
    """Mapper must not upgrade; status comes only from to_external(result.verdict)."""
    inputs = [
        ComplianceInput(
            canonical_name="water",
            flags={},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
        ComplianceInput(
            canonical_name="",
            flags={},
            knowledge_state="UNCLASSIFIED",
            trusted=False,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
    ]
    # Simulate evaluate outcome for mixed list: aggregate UNCERTAIN
    result = ComplianceResult(
        Verdict.UNCERTAIN,
        matched_contains=[],
        matched_may_contain=[],
        caution_reasons=["unverified_knowledge:vegan:"],
        breakdown={},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.status == VerdictStatus.UNCERTAIN
    assert v.status.value == to_external(result.verdict)
    assert v.status != VerdictStatus.SAFE


def test_map_ike2_triggered_restrictions_excludes_safe_breakdown_rows():
    """A SAFE row in breakdown (e.g. peanut_allergy) must not leak into
    triggered_restrictions just because the ingredient is also in
    matched_contains for an unrelated FAIL restriction (vegan)."""
    inputs = [
        ComplianceInput(
            canonical_name="gelatin",
            flags={"animal_origin": True},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
        ComplianceInput(
            canonical_name="peanut",
            flags={},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
    ]
    result = ComplianceResult(
        Verdict.FAIL,
        matched_contains=["gelatin", "peanut"],
        matched_may_contain=[],
        caution_reasons=["vegan:gelatin"],
        breakdown={
            ("gelatin", "vegan"): Verdict.FAIL,
            ("peanut", "peanut_allergy"): Verdict.SAFE,
        },
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.triggered_restrictions == ["vegan"]


def test_map_ike2_may_contain_goes_to_informational_ingredients():
    """matched_may_contain (trace/may-contain minors) must surface as
    informational_ingredients, not be discarded."""
    inputs = [
        ComplianceInput(
            canonical_name="peanut",
            flags={},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=True,
        )
    ]
    result = ComplianceResult(
        Verdict.WARN,
        matched_contains=[],
        matched_may_contain=["peanut"],
        caution_reasons=["peanut_allergy:peanut"],
        breakdown={("peanut", "peanut_allergy"): Verdict.WARN},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert "peanut" in v.informational_ingredients


def test_map_ike2_confidence_score_safe_no_uncertain():
    inputs = [
        ComplianceInput(
            canonical_name="water",
            flags={},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        )
    ]
    result = ComplianceResult(
        Verdict.SAFE,
        matched_contains=[],
        matched_may_contain=[],
        caution_reasons=[],
        breakdown={("water", "vegan"): Verdict.SAFE},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.confidence_score == 1.0


def test_map_ike2_confidence_score_zero_when_not_safe():
    result = ComplianceResult(
        Verdict.FAIL,
        matched_contains=["gelatin"],
        matched_may_contain=[],
        caution_reasons=["vegan:gelatin"],
        breakdown={("gelatin", "vegan"): Verdict.FAIL},
    )
    v = map_ike2_to_compliance_verdict(result, [])
    assert v.confidence_score == 0.0


# ---------------------------------------------------------------------------
# Task 4: bridge primary path + fail-closed UNCERTAIN
# ---------------------------------------------------------------------------

def test_ike2_exception_returns_uncertain_not_legacy(monkeypatch):
    import core.bridge as bridge

    def boom(*args, **kwargs):
        raise RuntimeError("ike2 down")

    monkeypatch.setattr(bridge, "_run_ike2_compliance", boom)  # extract helper for testability

    # Legacy would say SAFE for water — must not be returned
    v = run_new_engine_chat(["water"], restriction_ids=["vegan"], use_api_fallback=False)
    assert v.status == VerdictStatus.UNCERTAIN


def test_ike2_success_returned_not_legacy(monkeypatch):
    from core.models.verdict import ComplianceVerdict, VerdictStatus
    import core.bridge as bridge

    fake = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegan"],
        triggered_ingredients=["gelatin"],
    )
    monkeypatch.setattr(
        bridge,
        "_run_ike2_compliance",
        lambda *a, **k: fake,
    )
    # Force legacy to SAFE if it were used
    monkeypatch.setattr(
        bridge,
        "_schedule_legacy_diff",
        lambda *a, **k: None,
    )
    v = run_new_engine_chat(["gelatin"], restriction_ids=["vegan"], use_api_fallback=False)
    assert v is fake or v.status == VerdictStatus.NOT_SAFE


# ---------------------------------------------------------------------------
# Task 5: legacy diff runs in background, does not block the chat response
# ---------------------------------------------------------------------------

def test_legacy_diff_does_not_block_response(monkeypatch):
    import core.bridge as bridge

    def slow_legacy(*args, **kwargs):
        time.sleep(2.0)
        return None

    monkeypatch.setattr(bridge, "_run_legacy_diff_job", slow_legacy)
    # Ensure IKE-2 path is fast
    t0 = time.perf_counter()
    v = run_new_engine_chat(["water"], restriction_ids=["vegan"], use_api_fallback=False)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5  # must not wait for 2s legacy
    assert v.status in (VerdictStatus.SAFE, VerdictStatus.UNCERTAIN, VerdictStatus.NOT_SAFE)


# ---------------------------------------------------------------------------
# Task 6: IKE-2 wins when engines disagree
# ---------------------------------------------------------------------------

def test_response_is_ike2_when_disagrees_with_legacy(monkeypatch):
    import core.bridge as bridge
    from core.models.verdict import ComplianceVerdict, VerdictStatus

    ike2_v = ComplianceVerdict(status=VerdictStatus.NOT_SAFE, triggered_ingredients=["gelatin"])
    captured = {}

    monkeypatch.setattr(bridge, "map_ike2_to_compliance_verdict", lambda *a, **k: ike2_v)
    monkeypatch.setattr(
        bridge,
        "_run_ike2_compliance",
        lambda *a, **k: ("result", "inputs", {}),
    )

    def capture_schedule(ingredients, rids, primary_status, prepared):
        captured["primary_status"] = primary_status

    monkeypatch.setattr(bridge, "_schedule_legacy_diff", capture_schedule)

    out = run_new_engine_chat(["gelatin"], restriction_ids=["vegan"], use_api_fallback=False)
    assert out.status == VerdictStatus.NOT_SAFE
    assert captured["primary_status"] == "NOT_SAFE"
