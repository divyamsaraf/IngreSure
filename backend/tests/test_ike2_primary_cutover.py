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
