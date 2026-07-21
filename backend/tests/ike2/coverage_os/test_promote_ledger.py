import pytest
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def test_non_promotable_blocks_lookup(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("roman bean", "roman bean")
    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="not a food commodity",
    )
    hit = led.find_non_promotable(key)
    assert hit is not None
    assert hit["kind"] == "confirmed_non_promotable"


def test_human_promote_requires_reviewer_fields(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")
    with pytest.raises(ValueError):
        led.append_promoted(
            candidate_key=key,
            rule_id="closed_form_plant_v1",
            source="human",
            payload={"canonical": "broccoli"},
            auto=False,
            reviewer_id=None,
            approval_rationale=None,
        )
    led.append_promoted(
        candidate_key=key,
        rule_id="closed_form_plant_v1",
        source="human",
        payload={"canonical": "broccoli", "flags": {"plant_origin": True}},
        auto=False,
        reviewer_id="reviewer-1",
        approval_rationale="single-origin vegetable",
    )
    row = led.latest_promoted(key)
    assert row["reviewer_id"] == "reviewer-1"
    assert row["approval_rationale"]
    assert row["version"] == 1


def test_demote_increments_and_marks_inactive(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")
    led.append_promoted(
        candidate_key=key,
        rule_id="closed_form_plant_v1",
        source="auto",
        payload={"canonical": "broccoli"},
        auto=True,
    )
    assert led.latest_promoted(key) is not None
    assert led.latest_promoted(key)["version"] == 1
    demoted = led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert demoted["version"] == 2
    assert demoted["prior_version"] == 1
    assert led.latest_promoted(key) is None


def test_rejected_human_promote_writes_nothing(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")
    with pytest.raises(ValueError):
        led.append_promoted(
            candidate_key=key,
            rule_id="closed_form_plant_v1",
            source="human",
            payload={"canonical": "broccoli"},
            auto=False,
            reviewer_id=None,
            approval_rationale=None,
        )
    assert led.path.read_text(encoding="utf-8").strip() == ""
    assert led.latest_promoted(key) is None
