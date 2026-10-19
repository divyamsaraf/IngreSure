# backend/tests/ike2/coverage_os/test_hybrid_gate_role_only.py
from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def test_role_only_payload_is_human_fail_closed(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("almond", "almond"),
        candidate_name="almond",
        flags={},  # role-only: no plant_origin — cannot satisfy auto_promote predicate
        ledger=led,
        ontology={"ingredients": []},
    )
    # GateDecision.action Literal (Phase 1): auto_promote | human_approval | rejected
    assert d.action == "human_approval"
    assert d.rule_id == "human_fail_closed"
