from types import SimpleNamespace

from core.knowledge.ike2.compliance import ComplianceResult
from core.knowledge.ike2.response import assemble, is_triggered
from core.knowledge.ike2.verdict import Verdict


def _resolved(canonical="x", animal_origin=False, peanut_source=False):
    flags = {"animal_origin": animal_origin, "peanut_source": peanut_source}
    return SimpleNamespace(canonical_name=canonical, flags=flags)


def _result(verdict, caution=None, matched_contains=None, matched_may_contain=None):
    return ComplianceResult(
        verdict,
        matched_contains or [],
        matched_may_contain or [],
        caution or [],
        {},
    )


def _jain():
    return SimpleNamespace(restrictions={"jain": "preference"})


def _pref_peanut():
    return SimpleNamespace(restrictions={"peanut": "preference"})


def test_non_triggering_ingredient_not_marked_triggered():
    yam = _resolved(canonical="sweet_potato", animal_origin=False)
    payload = assemble([yam], _result(Verdict.SAFE), profile=_jain())
    card = next(c for c in payload["audit"] if c["canonical_name"] == "sweet_potato")
    assert card["triggered"] is False


def test_external_verdict_mapping():
    payload = assemble(
        [], _result(Verdict.WARN, caution=["may_contain_trace"]), profile=_jain()
    )
    assert payload["external_verdict"] == "UNCERTAIN"
    assert "may_contain_trace" in payload["caution_reasons"]


def test_b2b_mode_exposes_full_breakdown_and_strict_headline():
    r = _result(Verdict.WARN, matched_may_contain=["peanut"])  # preference trace -> WARN
    payload = assemble([], r, profile=_pref_peanut(), mode="b2b")
    assert payload["matched_may_contain"] == ["peanut"]
    assert payload["external_verdict"] == "NOT_SAFE"  # b2b strict treats trace as trigger
