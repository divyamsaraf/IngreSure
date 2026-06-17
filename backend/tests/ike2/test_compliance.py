from types import SimpleNamespace

import pytest

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict


# ---- minimal object builders ------------------------------------------------
def _resolved(
    canonical="x",
    animal_origin=False,
    peanut_source=False,
    dairy_source=False,
    knowledge_state="VERIFIED",
    trusted=True,
    verdict_cap=None,
    alcohol_role=None,
    trace=False,
):
    flags = {
        "animal_origin": animal_origin,
        "peanut_source": peanut_source,
        "dairy_source": dairy_source,
        "alcohol_role": alcohol_role,
    }
    return SimpleNamespace(
        canonical_name=canonical,
        flags=flags,
        knowledge_state=knowledge_state,
        trusted=trusted,
        verdict_cap=verdict_cap,
        alcohol_role=alcohol_role,
        trace=trace,
    )


def _profile(restriction, severity="medical"):
    return SimpleNamespace(restrictions={restriction: severity})


def _vegan():
    return SimpleNamespace(restrictions={"vegan": "preference"})


# ---- rule fixtures ----------------------------------------------------------
@pytest.fixture
def rule_vegan():
    return SimpleNamespace(
        restriction="vegan",
        kind="flag",
        trigger_flag="animal_origin",
        min_knowledge_state="UNCLASSIFIED",
    )


@pytest.fixture
def rule_peanut():
    return SimpleNamespace(
        restriction="peanut",
        kind="flag",
        trigger_flag="peanut_source",
        min_knowledge_state="UNCLASSIFIED",
    )


@pytest.fixture
def rule_no_alcohol():
    return SimpleNamespace(
        restriction="alcohol",
        kind="alcohol",
        trigger_flag=None,
        min_knowledge_state="UNCLASSIFIED",
    )


@pytest.fixture
def rule_jain():
    return SimpleNamespace(
        restriction="jain",
        kind="flag",
        trigger_flag="animal_origin",
        min_knowledge_state="UNCLASSIFIED",
    )


# ---- tests ------------------------------------------------------------------
def test_unclassified_never_safe(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="UNCLASSIFIED", trusted=False)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) != Verdict.SAFE


def test_discovered_pass_caps_to_warn(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="DISCOVERED", trusted=True)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) == Verdict.WARN


def test_verdict_cap_caps_to_warn(rule_vegan):
    r = _resolved(
        animal_origin=False, knowledge_state="VERIFIED", trusted=True, verdict_cap="WARN"
    )
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) == Verdict.WARN


def test_untrusted_resolution_never_safe(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=False)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) != Verdict.SAFE


def test_animal_fails_vegan(rule_vegan):
    r = _resolved(animal_origin=True, knowledge_state="LOCKED", trusted=True)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]).verdict == Verdict.FAIL


def test_medical_may_contain_fails_preference_warns(rule_peanut):
    r = _resolved(peanut_source=True, trusted=True, trace=True)  # may_contain peanut
    assert (
        evaluate([r], _profile("peanut", "medical"), [rule_peanut]).verdict
        == Verdict.FAIL
    )
    assert (
        evaluate([r], _profile("peanut", "preference"), [rule_peanut]).verdict
        == Verdict.WARN
    )


def test_unknown_severity_defaults_medical(rule_peanut):
    r = _resolved(peanut_source=True, trusted=True, trace=True)
    assert (
        evaluate([r], _profile("peanut", severity=None), [rule_peanut]).verdict
        == Verdict.FAIL
    )


def test_alcohol_ingredient_fails_trace_warns(rule_no_alcohol):
    ing = _resolved(alcohol_role="ingredient", trusted=True)
    ferm = _resolved(alcohol_role="fermentation_trace", trusted=True)
    assert (
        evaluate([ing], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict
        == Verdict.FAIL
    )
    assert (
        evaluate([ferm], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict
        == Verdict.WARN
    )


def test_compound_term_caps_to_warn(rule_jain):
    r = _resolved(
        canonical="spices", knowledge_state="VERIFIED", trusted=True, verdict_cap="WARN"
    )
    assert (
        evaluate([r], _profile("jain", "preference"), [rule_jain]).verdict
        == Verdict.WARN
    )


def test_untrusted_trace_is_uncertain_not_avoid(rule_peanut):
    r = _resolved(peanut_source=True, trusted=False, trace=True)  # low-confidence trace
    assert (
        evaluate([r], _profile("peanut", "medical"), [rule_peanut]).verdict
        == Verdict.UNCERTAIN
    )
