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


def test_alcohol_none_sentinel_string_is_safe(rule_no_alcohol):
    # The adapter/DB store the STRING "none" (NOT NULL DEFAULT 'none') for
    # non-alcohol ingredients. Compliance must treat it as not-triggered, otherwise
    # every water/salt/sugar becomes WARN for an alcohol-restricted user.
    r = _resolved(alcohol_role="none", knowledge_state="VERIFIED", trusted=True)
    assert (
        evaluate([r], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict
        == Verdict.SAFE
    )


def test_alcohol_unknown_role_stays_cautious(rule_no_alcohol):
    # Defense in depth: a role outside the known set must never resolve SAFE.
    r = _resolved(alcohol_role="mystery", knowledge_state="VERIFIED", trusted=True)
    assert (
        evaluate([r], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict
        != Verdict.SAFE
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


def test_uncovered_restriction_is_never_safe(rule_vegan):
    # A profile restriction with no matching rule must not be silently dropped:
    # vegan passes SAFE, but peanut has no rule -> the peanut restriction was never
    # evaluated, so the headline verdict must degrade to UNCERTAIN, not SAFE.
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True)
    profile = SimpleNamespace(restrictions={"peanut": "medical", "vegan": "preference"})
    result = evaluate([r], profile, [rule_vegan])
    assert result.verdict == Verdict.UNCERTAIN
    assert any("peanut" in c for c in result.caution_reasons)


def test_full_coverage_resolves_safe(rule_vegan):
    # Guard against the coverage check over-firing: a single fully-covered
    # restriction on a clean, verified ingredient still resolves SAFE.
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True)
    assert evaluate([r], _vegan(), [rule_vegan]).verdict == Verdict.SAFE


def test_medical_may_contain_through_seam(rule_peanut):
    """Product-level trace from parser -> seam -> compliance (not hand-built trace)."""
    from core.knowledge.ike2.input_layer import parse_atoms
    from core.knowledge.ike2.seam import to_compliance_input

    peanut_atom = next(a for a in parse_atoms("water, contains 2% or less: peanuts") if "peanut" in a.name)
    assert peanut_atom.trace is True

    group = SimpleNamespace(
        canonical_name=peanut_atom.name, peanut_source=True, tree_nut_source=False,
        knowledge_state="VERIFIED", alcohol_role="none", alcohol_content=None,
        verdict_cap=None, uncertainty_flags=[],
    )
    ci = to_compliance_input(
        SimpleNamespace(group=group, trusted=True),
        trace=peanut_atom.trace,
    )
    assert evaluate([ci], _profile("peanut", "medical"), [rule_peanut]).verdict == Verdict.FAIL


def test_medical_may_contain_statement_through_seam(rule_peanut):
    from core.knowledge.ike2.input_layer import parse_atoms
    from core.knowledge.ike2.seam import to_compliance_input

    peanut_atom = next(
        a for a in parse_atoms("water, flour. May contain: peanuts") if "peanut" in a.name
    )
    assert peanut_atom.may_contain is True
    assert peanut_atom.trace is False

    group = SimpleNamespace(
        canonical_name=peanut_atom.name, peanut_source=True, tree_nut_source=False,
        knowledge_state="VERIFIED", alcohol_role="none", alcohol_content=None,
        verdict_cap=None, uncertainty_flags=[],
    )
    ci = to_compliance_input(
        SimpleNamespace(group=group, trusted=True),
        trace=peanut_atom.trace,
        may_contain=peanut_atom.may_contain,
    )
    assert evaluate([ci], _profile("peanut", "medical"), [rule_peanut]).verdict == Verdict.FAIL


def test_species_match_triggers_fail():
    rule = SimpleNamespace(
        restriction="halal",
        kind="species_match",
        trigger_flag=None,
        match_value="pig",
        action="FAIL",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(animal_origin=True, knowledge_state="VERIFIED", trusted=True)
    r.flags["animal_species"] = "pig"
    assert evaluate([r], _profile("halal", "preference"), [rule]).verdict == Verdict.FAIL


def test_species_match_porcine_gelatin_triggers_fail():
    rule = SimpleNamespace(
        restriction="halal",
        kind="species_match",
        trigger_flag=None,
        match_value="pig",
        action="FAIL",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(animal_origin=True, knowledge_state="VERIFIED", trusted=True)
    r.flags["animal_species"] = "bovine/porcine/fish depending on source"
    assert evaluate([r], _profile("halal", "preference"), [rule]).verdict == Verdict.FAIL


def test_species_unknown_with_animal_origin_is_uncertain():
    rule = SimpleNamespace(
        restriction="halal",
        kind="species_match",
        trigger_flag=None,
        match_value="pig",
        action="FAIL",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(animal_origin=True, knowledge_state="VERIFIED", trusted=True)
    r.flags["animal_species"] = None
    assert evaluate([r], _profile("halal", "preference"), [rule]).verdict == Verdict.UNCERTAIN


def test_meat_fish_derived_from_fish_source_without_animal_origin():
    rule = SimpleNamespace(
        restriction="vegetarian",
        kind="meat_fish_derived",
        trigger_flag=None,
        match_value=True,
        action="FAIL",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True)
    r.flags["fish_source"] = True
    assert evaluate([r], _profile("vegetarian", "preference"), [rule]).verdict == Verdict.FAIL


def test_alcohol_content_gt_zero_fails():
    rule = SimpleNamespace(
        restriction="halal",
        kind="alcohol_content",
        trigger_flag=None,
        match_value=0,
        action="FAIL",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(alcohol_role="none", knowledge_state="VERIFIED", trusted=True)
    r.flags["alcohol_content"] = 5.0
    assert evaluate([r], _profile("halal", "preference"), [rule]).verdict == Verdict.FAIL


def test_rule_action_warn():
    rule = SimpleNamespace(
        restriction="jain",
        kind="flag",
        trigger_flag="fermented",
        match_value=True,
        action="WARN",
        min_knowledge_state="UNCLASSIFIED",
    )
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True)
    r.flags["fermented"] = True
    assert evaluate([r], _profile("jain", "preference"), [rule]).verdict == Verdict.WARN


def test_verdict_cap_never_promotes_safe_to_firm_safe(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True, verdict_cap="WARN")
    assert evaluate([r], _profile("vegan", "preference"), [rule_vegan]).verdict != Verdict.SAFE


def test_definite_fail_not_downgraded_to_safe(rule_vegan):
    r = _resolved(animal_origin=True, knowledge_state="LOCKED", trusted=True)
    assert evaluate([r], _profile("vegan", "medical"), [rule_vegan]).verdict == Verdict.FAIL
