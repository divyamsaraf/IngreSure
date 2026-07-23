from __future__ import annotations

from core.knowledge.ike2.coverage_os.induction.precision import (
    DecisionRecord,
    demote_reason_is_safety,
    iter_induced_decisions,
    measure_precision,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


def test_precision_a_a1_a2_thresholds():
    records = [
        DecisionRecord(f"k{i}", True, "plant_closed") for i in range(40)
    ] + [
        DecisionRecord(f"d{i}", True, "animalish") for i in range(9)
    ] + [
        DecisionRecord("d9", True, "animalish"),
    ]
    report = measure_precision(records, window=50)
    assert report.n_decisions == 50
    assert report.meets_a
    assert report.a1_n == 10
    assert report.meets_a1
    assert report.meets_a2


def test_a2_fails_on_safety_demote():
    records = [DecisionRecord(f"k{i}", True, "plant_closed") for i in range(50)]
    records[0] = DecisionRecord("k0", True, "plant_closed", demoted_for_safety=True)
    report = measure_precision(records, window=50)
    assert not report.meets_a2


def test_demote_reason_is_safety():
    assert demote_reason_is_safety("demoted for safety — wrong animal flag")
    assert demote_reason_is_safety("SAFETY")
    assert not demote_reason_is_safety("typo fix")


def test_iter_induced_decisions_from_real_ledger(tmp_path):
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")
    ledger.append_promoted(
        candidate_key="broccoli florets=>broccoli",
        rule_id="closed_form_plant_v1",
        source="phase2b_induction",
        payload={
            "write_kind": "variant_alias",
            "induction": {"safety_class": "plant_closed", "frequency": 5},
        },
        auto=False,
        reviewer_id="r1",
        approval_rationale="ok",
    )
    ledger.append_promoted(
        candidate_key="gelatin powder=>gelatin",
        rule_id="human_animal_derived",
        source="phase2b_induction",
        payload={
            "write_kind": "variant_alias",
            "induction": {"safety_class": "animalish", "frequency": 3},
        },
        auto=False,
        reviewer_id="r1",
        approval_rationale="ok",
    )
    ledger.append_demoted(
        candidate_key="gelatin powder=>gelatin",
        reason="demoted for safety — incorrect animal routing",
    )
    ledger.append_non_promotable(
        candidate_key="junk=>junk",
        rule_id="induction_reviewer_reject",
        source="phase2b_induction",
        reason="reviewer_reject",
        payload={"induction": {"safety_class": "role_only"}},
    )
    ledger.append_promoted(
        candidate_key="noise=>noise",
        rule_id="closed_form_plant_v1",
        source="phase2a_role_seed",
        payload={"induction": {"safety_class": "plant_closed"}},
        auto=False,
        reviewer_id="r1",
        approval_rationale="seed",
    )

    records = iter_induced_decisions(ledger)
    by_key = {r.candidate_key: r for r in records}
    assert set(by_key) == {
        "broccoli florets=>broccoli",
        "gelatin powder=>gelatin",
        "junk=>junk",
    }
    assert by_key["broccoli florets=>broccoli"].accepted is True
    assert by_key["broccoli florets=>broccoli"].demoted_for_safety is False
    assert by_key["gelatin powder=>gelatin"].accepted is True
    assert by_key["gelatin powder=>gelatin"].demoted_for_safety is True
    assert by_key["gelatin powder=>gelatin"].safety_class == "animalish"
    assert by_key["junk=>junk"].accepted is False
    assert by_key["junk=>junk"].safety_class == "role_only"

    report = measure_precision(records, window=50)
    assert report.n_decisions == 3
    assert report.a2_demote_for_safety_count == 1
    assert not report.meets_a2
