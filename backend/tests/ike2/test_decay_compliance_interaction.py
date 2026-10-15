"""Item 4.1 / Item 34: decay must remove firm SAFE, never silence a true FAIL."""
from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.decay import next_decay_state, TTL_AUTO_CLASSIFIED_DAYS
from core.knowledge.ike2.verdict import Verdict


def _ci(*, knowledge_state: str, animal_origin: bool = False, peanut_source: bool = False):
    return SimpleNamespace(
        canonical_name="x",
        flags={
            "animal_origin": animal_origin,
            "peanut_source": peanut_source,
        },
        knowledge_state=knowledge_state,
        trusted=True,
        verdict_cap=None,
        alcohol_role="none",
        trace=False,
        may_contain=False,
    )


def test_demotion_auto_to_discovered_removes_firm_safe_on_clean_pass():
    """Clean pass: AUTO_CLASSIFIED can be firm SAFE; DISCOVERED cannot."""
    rule = SimpleNamespace(
        restriction="vegan",
        kind="flag",
        trigger_flag="animal_origin",
        action="FAIL",
        min_knowledge_state="DISCOVERED",
    )
    profile = SimpleNamespace(restrictions={"vegan": "preference"})

    before = evaluate([_ci(knowledge_state="AUTO_CLASSIFIED")], profile, [rule])
    assert before.verdict == Verdict.SAFE

    demoted = next_decay_state("AUTO_CLASSIFIED", TTL_AUTO_CLASSIFIED_DAYS)
    assert demoted == "DISCOVERED"

    after = evaluate([_ci(knowledge_state=demoted)], profile, [rule])
    assert after.verdict != Verdict.SAFE
    assert after.verdict == Verdict.WARN


def test_demotion_verified_to_auto_keeps_triggered_fail():
    """Item 34: positive hazard FAIL survives KS demotion (decay never silences Avoid)."""
    rule = SimpleNamespace(
        restriction="peanut_allergy",
        kind="flag",
        trigger_flag="peanut_source",
        action="FAIL",
        min_knowledge_state="VERIFIED",
    )
    profile = SimpleNamespace(restrictions={"peanut_allergy": "medical"})

    before = evaluate(
        [_ci(knowledge_state="VERIFIED", peanut_source=True)], profile, [rule]
    )
    assert before.verdict == Verdict.FAIL

    demoted = next_decay_state("VERIFIED", 180)
    assert demoted == "AUTO_CLASSIFIED"

    after = evaluate(
        [_ci(knowledge_state=demoted, peanut_source=True)], profile, [rule]
    )
    assert after.verdict == Verdict.FAIL


def test_discovered_with_true_hazard_flag_still_fails():
    """Pre-decay exposure class: DISCOVERED + true allergen flag must Avoid, not Depends."""
    rule = SimpleNamespace(
        restriction="peanut_allergy",
        kind="flag",
        trigger_flag="peanut_source",
        action="FAIL",
        min_knowledge_state="AUTO_CLASSIFIED",
    )
    profile = SimpleNamespace(restrictions={"peanut_allergy": "medical"})

    result = evaluate(
        [_ci(knowledge_state="DISCOVERED", peanut_source=True)], profile, [rule]
    )
    assert result.verdict == Verdict.FAIL
