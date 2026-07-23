# backend/tests/ike2/coverage_os/induction/test_phase2b_exit.py
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.precision import (
    DecisionRecord,
    iter_induced_decisions,
    measure_precision,
)
from core.knowledge.ike2.coverage_os.induction.propose_alias import propose_alias
from core.knowledge.ike2.coverage_os.induction.propose_role import propose_role_backfill
from core.knowledge.ike2.coverage_os.induction.submit import submit_induced
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger
from core.knowledge.ike2.coverage_os.promote_writer import commit_demotion


def test_round_trip_alias_and_role_force_human(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    aliases_path = tmp_path / "variant_aliases.json"
    ontology = {
        "ingredients": [
            {"canonical_name": "broccoli", "plant_origin": True},
            {"canonical_name": "vinegar", "plant_origin": True},
        ]
    }
    ontology_path.write_text(json.dumps(ontology), encoding="utf-8")
    aliases_path.write_text(
        json.dumps({"aliases": {}, "coverage_os_managed_aliases": []}),
        encoding="utf-8",
    )
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")

    alias_cand = propose_alias(
        ClusterItem("broccoli florets", "broccoli florets", 5, "M4_morphology"),
        ontology=ontology,
        alias_table={},
    )
    assert alias_cand is not None
    alias_row = submit_induced(
        alias_cand,
        ledger=ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        ontology=ontology,
        reviewer_id="exit",
        approval_rationale="alias ok",
        decision="accept",
    )
    assert alias_row is not None
    assert alias_row["auto"] is False
    assert alias_row["payload"]["induction"]["safety_class"] == "plant_closed"
    aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
    assert aliases["aliases"].get("broccoli florets") == "broccoli"

    role_cands = propose_role_backfill(
        ontology=ontology,
        tear_evidence={"vinegar": "culinary_keep"},
    )
    assert len(role_cands) == 1
    role_row = submit_induced(
        role_cands[0],
        ledger=ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        ontology=ontology,
        reviewer_id="exit",
        approval_rationale="role ok",
        decision="accept",
    )
    assert role_row is not None
    assert role_row["auto"] is False
    assert role_row["payload"]["induction"]["safety_class"] == "plant_closed"

    # Demote alias retracts L2
    entry = {
        "candidate_key": alias_row["candidate_key"],
        "payload": alias_row["payload"],
    }
    commit_demotion(
        entry,
        ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        reason="exit demote",
        candidate_key=alias_row["candidate_key"],
    )
    aliases_after = json.loads(aliases_path.read_text(encoding="utf-8"))
    assert "broccoli florets" not in (aliases_after.get("aliases") or {})

    decisions = iter_induced_decisions(ledger)
    assert any(d.candidate_key == alias_row["candidate_key"] and d.accepted for d in decisions)
    assert any(d.candidate_key == role_row["candidate_key"] and d.accepted for d in decisions)


def test_phase2a_baseline_fixture_still_present():
    p = Path(__file__).resolve().parents[1] / "fixtures" / "phase2a_matrix_baseline.json"
    assert p.exists()


def test_precision_helpers_ready_for_ops_window():
    records = [
        DecisionRecord(f"k{i}", True, "plant_closed") for i in range(40)
    ] + [
        DecisionRecord(f"d{i}", True, "animalish") for i in range(10)
    ]
    report = measure_precision(records, window=50)
    assert report.meets_a and report.meets_a1 and report.meets_a2
