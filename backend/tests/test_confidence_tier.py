"""Phase 3 trust hardening: Safe copy must be label-scoped (never an absolute
medical guarantee) and the audit payload must carry a display-only
confidence tier ('verified' / 'standard' / 'limited') derived from the
knowledge_state of the facts that drove the verdict."""
from core.bridge import map_ike2_to_compliance_verdict
from core.knowledge.ike2.compliance import ComplianceResult
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.response_composer import (
    build_ingredient_audit_payload,
    compose_verdict,
    compose_verdict_explanation,
)

_ABSOLUTE_SAFETY_PHRASES = (
    "safe for you to eat",
    "safe to eat",
    "guaranteed safe",
    "100% safe",
    "medically safe",
    "certified safe",
)


class _Profile:
    dietary_preference = "Vegan"
    allergens = []
    lifestyle = []


def _ci(canonical_name, knowledge_state="LOCKED", trusted=True):
    return ComplianceInput(
        canonical_name=canonical_name,
        flags={},
        knowledge_state=knowledge_state,
        trusted=trusted,
        alcohol_role=None,
        verdict_cap=None,
        trace=False,
    )


def _safe_result(names):
    return ComplianceResult(
        Verdict.SAFE,
        matched_contains=[],
        matched_may_contain=[],
        caution_reasons=[],
        breakdown={(name, "vegan"): Verdict.SAFE for name in names},
    )


# ---------------------------------------------------------------------------
# evidence_tier / confidence_tier computation
# ---------------------------------------------------------------------------
def test_evidence_tier_verified_when_all_locked():
    inputs = [_ci("water", "LOCKED"), _ci("salt", "VERIFIED")]
    v = map_ike2_to_compliance_verdict(_safe_result(["water", "salt"]), inputs)
    assert v.evidence_tier == "verified"


def test_evidence_tier_standard_when_mid_tier():
    inputs = [_ci("water", "LOCKED"), _ci("some_db_row", "AUTO_CLASSIFIED")]
    v = map_ike2_to_compliance_verdict(_safe_result(["water", "some_db_row"]), inputs)
    assert v.evidence_tier == "standard"


def test_evidence_tier_limited_when_untrusted():
    inputs = [_ci("water", "LOCKED"), _ci("mystery", "DISCOVERED", trusted=False)]
    v = map_ike2_to_compliance_verdict(_safe_result(["water"]), inputs)
    assert v.evidence_tier == "limited"


def test_evidence_tier_limited_when_discovered():
    inputs = [_ci("water", "LOCKED"), _ci("crowd_sourced", "DISCOVERED")]
    v = map_ike2_to_compliance_verdict(_safe_result(["water", "crowd_sourced"]), inputs)
    assert v.evidence_tier == "limited"


def test_evidence_tier_defaults_to_standard_with_no_inputs():
    v = map_ike2_to_compliance_verdict(_safe_result([]), [])
    assert v.evidence_tier == "standard"


def test_compliance_verdict_default_evidence_tier_is_standard():
    v = ComplianceVerdict(status=VerdictStatus.SAFE)
    assert v.evidence_tier == "standard"
    assert v.to_dict()["evidence_tier"] == "standard"


# ---------------------------------------------------------------------------
# Audit payload carries confidence_tier
# ---------------------------------------------------------------------------
def test_audit_payload_carries_confidence_tier_verified():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE, evidence_tier="verified")
    payload = build_ingredient_audit_payload(verdict=verdict, profile=_Profile(), ingredients=["water"])
    assert payload["confidence_tier"] == "verified"


def test_audit_payload_carries_confidence_tier_limited():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE, evidence_tier="limited")
    payload = build_ingredient_audit_payload(verdict=verdict, profile=_Profile(), ingredients=["water"])
    assert payload["confidence_tier"] == "limited"


def test_audit_payload_defaults_confidence_tier_standard():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE)
    payload = build_ingredient_audit_payload(verdict=verdict, profile=_Profile(), ingredients=["water"])
    assert payload["confidence_tier"] == "standard"


# ---------------------------------------------------------------------------
# Safe copy is label-scoped, never an absolute medical guarantee
# ---------------------------------------------------------------------------
def test_compose_verdict_explanation_safe_copy_is_scoped():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE)
    expl = compose_verdict_explanation(verdict, _Profile(), ["water", "salt"])
    assert "no disqualifying ingredients found" in expl.lower()
    lowered = expl.lower()
    for phrase in _ABSOLUTE_SAFETY_PHRASES:
        assert phrase not in lowered


def test_compose_verdict_explanation_safe_single_ingredient_is_scoped():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE)
    expl = compose_verdict_explanation(verdict, _Profile(), ["water"])
    assert "no disqualifying ingredients found" in expl.lower()


def test_compose_verdict_safe_copy_is_scoped_not_absolute():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE)
    text = compose_verdict(verdict, _Profile(), ["water", "salt"])
    lowered = text.lower()
    assert "no disqualifying ingredients found" in lowered
    for phrase in _ABSOLUTE_SAFETY_PHRASES:
        assert phrase not in lowered


def test_compose_verdict_not_safe_rest_are_safe_copy_is_scoped():
    """Even the 'rest are safe' aside inside a NOT_SAFE reply must not read
    as an absolute safety claim."""
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegan"],
        triggered_ingredients=["gelatin"],
    )
    text = compose_verdict(verdict, _Profile(), ["gelatin", "water"])
    lowered = text.lower()
    for phrase in _ABSOLUTE_SAFETY_PHRASES:
        assert phrase not in lowered
