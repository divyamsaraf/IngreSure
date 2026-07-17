import importlib

import pytest

from core.bridge import map_ike2_to_compliance_verdict
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
