"""Property-based tests for IKE-2 safety invariants (INV-1..INV-9 in
docs/superpowers/specs/2026-07-20-zero-false-safe-trust-architecture.md §2).

Golden-case tests (test_must_never_be_safe.py, test_false_safe_root_fixes.py)
catch known false-Safe examples. This file uses hypothesis to generate many
inputs per invariant so whole *classes* of false-Safe bugs are caught, not
just the specific rows already in a corpus.

Ingredient canonical names used here are synthetic (``__test_atom__`` style)
so they never collide with real ``truth_anchor`` entries — a collision would
let Tier-1 overlay (``_effective_flags``) silently inject extra flags and
make the test non-deterministic w.r.t. the flags we intend to exercise.
"""
from __future__ import annotations

from types import SimpleNamespace

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from core.knowledge.ike2 import compliance as compliance_module
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict, aggregate, to_external

RULES = rules_module.seeded_rules()
ALL_RESTRICTIONS = sorted(rules_module.SUPPORTED_RESTRICTIONS)

# category (profile restriction id) -> boolean safety-flag column it triggers on.
ALLERGEN_FIELD_BY_RESTRICTION = {
    "peanut_allergy": "peanut_source",
    "tree_nut_allergy": "tree_nut_source",
    "soy_allergy": "soy_source",
    "sesame_allergy": "sesame_source",
    "fish_allergy": "fish_source",
    "shellfish_allergy": "shellfish_source",
    "mustard_allergy": "mustard_source",
    "lupin_allergy": "lupin_source",
    "celery_allergy": "celery_source",
    "onion_allergy": "onion_source",
    "garlic_allergy": "garlic_source",
    "gluten_free": "gluten_source",
    "celiac_strict": "gluten_source",
    "lactose_free": "dairy_source",
    "dairy_free": "dairy_source",
    "egg_free": "egg_source",
    "sulfite_sensitive": "sulphite_source",
}
MEDICAL_RESTRICTIONS = sorted(ALLERGEN_FIELD_BY_RESTRICTION)

# Restrictions where any non-empty origin uncertainty caps a clean pass below
# SAFE (compliance._uncertainty_ceiling's deny-by-default set).
CEILING_RESTRICTIONS = sorted(
    r
    for r in (compliance_module._VEGAN_RELIGIOUS | compliance_module._DAIRY_EGG)
    if r in rules_module.SUPPORTED_RESTRICTIONS
)

_FLAG_KEYS = (
    "peanut_source", "tree_nut_source", "soy_source", "sesame_source",
    "fish_source", "shellfish_source", "mustard_source", "lupin_source",
    "celery_source", "onion_source", "garlic_source", "gluten_source",
    "dairy_source", "egg_source", "sulphite_source", "animal_origin",
    "insect_derived", "bee_product",
)


def _ci(**overrides) -> ComplianceInput:
    base = dict(
        canonical_name="__test_atom__",
        flags={},
        knowledge_state="LOCKED",
        trusted=True,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
        may_contain=False,
    )
    base.update(overrides)
    return ComplianceInput(**base)


def _evaluate(ci_list, restrictions: dict):
    profile = SimpleNamespace(restrictions=restrictions)
    return evaluate(ci_list, profile, RULES)


# ---------------------------------------------------------------------------
# INV-2: untrusted resolution -> never Safe or Avoid (only Depends/UNCERTAIN).
# ---------------------------------------------------------------------------

@given(
    restriction=st.sampled_from(ALL_RESTRICTIONS),
    flag_bools=st.dictionaries(
        st.sampled_from(_FLAG_KEYS), st.one_of(st.booleans(), st.none()), max_size=6
    ),
    knowledge_state=st.sampled_from(
        ["UNCLASSIFIED", "DISCOVERED", "AUTO_CLASSIFIED", "CLASSIFIED", "VERIFIED", "LOCKED"]
    ),
)
@settings(max_examples=200)
def test_untrusted_never_safe_or_fail(restriction, flag_bools, knowledge_state):
    ci = _ci(flags=dict(flag_bools), knowledge_state=knowledge_state, trusted=False)
    result = _evaluate([ci], {restriction: "medical"})
    assert result.verdict not in (Verdict.SAFE, Verdict.FAIL), (
        restriction, flag_bools, knowledge_state, result.verdict,
    )


def test_untrusted_peanut_true_is_uncertain_not_fail():
    """Even a flag that would otherwise FAIL must not escalate when untrusted."""
    ci = _ci(flags={"peanut_source": True}, trusted=False)
    result = _evaluate([ci], {"peanut_allergy": "medical"})
    assert to_external(result.verdict) == "UNCERTAIN"


# ---------------------------------------------------------------------------
# INV-5: medical "may contain" -> Avoid, never Safe.
# ---------------------------------------------------------------------------

@given(restriction=st.sampled_from(MEDICAL_RESTRICTIONS))
@settings(max_examples=50)
def test_may_contain_medical_allergen_never_safe(restriction):
    field = ALLERGEN_FIELD_BY_RESTRICTION[restriction]
    ci = _ci(flags={field: True}, may_contain=True)
    result = _evaluate([ci], {restriction: "medical"})
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# INV-4: compound/umbrella terms (verdict_cap WARN) can never firm-SAFE.
# ---------------------------------------------------------------------------

@given(restriction=st.sampled_from(ALL_RESTRICTIONS))
@settings(max_examples=60)
def test_verdict_cap_warn_clean_pass_never_safe(restriction):
    ci = _ci(flags={}, verdict_cap="WARN")
    result = _evaluate([ci], {restriction: "medical"})
    assert result.verdict != Verdict.SAFE


# ---------------------------------------------------------------------------
# Deny-by-default uncertainty ceiling: non-empty uncertainty_flags on
# vegan/religious/dairy-egg restrictions must cap a clean pass below SAFE.
# ---------------------------------------------------------------------------

_flag_text = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
)


@given(restriction=st.sampled_from(CEILING_RESTRICTIONS), flag_text=_flag_text)
@settings(max_examples=100)
def test_uncertainty_flags_cap_vegan_religious_dairy_egg_never_safe(restriction, flag_text):
    assume("pku" not in flag_text and "banned_substance" not in flag_text)
    ci = _ci(flags={"animal_origin": False, "uncertainty_flags": [flag_text]})
    result = _evaluate([ci], {restriction: "preference"})
    assert result.verdict != Verdict.SAFE, (restriction, flag_text, result.verdict)


def test_vegan_uncertainty_flags_never_safe():
    ci = _ci(flags={"animal_origin": False, "uncertainty_flags": ["source_species_unspecified"]})
    result = _evaluate([ci], {"vegan": "preference"})
    assert result.verdict != Verdict.SAFE


# ---------------------------------------------------------------------------
# INV-6: explicit NULL safety flag != verified-false -> UNCERTAIN, never SAFE.
# ---------------------------------------------------------------------------

@given(restriction=st.sampled_from(MEDICAL_RESTRICTIONS))
@settings(max_examples=50)
def test_explicit_null_safety_flag_never_safe(restriction):
    field = ALLERGEN_FIELD_BY_RESTRICTION[restriction]
    ci = _ci(flags={field: None}, knowledge_state="AUTO_CLASSIFIED")
    result = _evaluate([ci], {restriction: "medical"})
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.UNCERTAIN


def test_peanut_source_explicit_none_uncertain_for_peanut_allergy():
    ci = _ci(flags={"peanut_source": None}, knowledge_state="AUTO_CLASSIFIED")
    result = _evaluate([ci], {"peanut_allergy": "medical"})
    assert to_external(result.verdict) == "UNCERTAIN"


# ---------------------------------------------------------------------------
# INV-1: worst-case aggregation. Any FAIL beats any number of SAFE/WARN/
# UNCERTAIN verdicts in the raw aggregate, and end-to-end across ingredients.
# ---------------------------------------------------------------------------

@given(
    n_safe=st.integers(min_value=0, max_value=10),
    n_fail=st.integers(min_value=1, max_value=10),
    n_warn=st.integers(min_value=0, max_value=5),
    n_uncertain=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100)
def test_aggregate_any_fail_dominates(n_safe, n_fail, n_warn, n_uncertain):
    verdicts = (
        [Verdict.SAFE] * n_safe
        + [Verdict.FAIL] * n_fail
        + [Verdict.WARN] * n_warn
        + [Verdict.UNCERTAIN] * n_uncertain
    )
    assert aggregate(verdicts) == Verdict.FAIL


def test_evaluate_worst_case_mix_of_safe_and_fail_is_fail():
    safe_ci = _ci(canonical_name="__test_safe__", flags={"peanut_source": False})
    fail_ci = _ci(canonical_name="__test_fail__", flags={"tree_nut_source": True})
    result = _evaluate(
        [safe_ci, fail_ci], {"peanut_allergy": "medical", "tree_nut_allergy": "medical"}
    )
    assert result.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# Pescatarian: land-animal meat FAILs, fish/shellfish alone must not FAIL.
# ---------------------------------------------------------------------------

@given(
    extra_false_flags=st.dictionaries(
        st.sampled_from(
            ["dairy_source", "egg_source", "insect_derived", "bee_product",
             "fish_source", "shellfish_source"]
        ),
        st.just(False),
        max_size=6,
    ),
)
@settings(max_examples=40)
def test_pescatarian_meat_land_derived_always_fails(extra_false_flags):
    flags = {"animal_origin": True, **extra_false_flags}
    ci = _ci(flags=flags, knowledge_state="DISCOVERED")
    result = _evaluate([ci], {"pescatarian": "preference"})
    assert result.verdict == Verdict.FAIL, (flags, result.verdict)


def test_pescatarian_fish_source_alone_not_fail():
    ci = _ci(flags={"animal_origin": True, "fish_source": True}, knowledge_state="DISCOVERED")
    result = _evaluate([ci], {"pescatarian": "preference"})
    assert result.verdict != Verdict.FAIL


def test_pescatarian_shellfish_source_alone_not_fail():
    ci = _ci(flags={"animal_origin": True, "shellfish_source": True}, knowledge_state="DISCOVERED")
    result = _evaluate([ci], {"pescatarian": "preference"})
    assert result.verdict != Verdict.FAIL
