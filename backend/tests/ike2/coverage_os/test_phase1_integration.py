# backend/tests/ike2/coverage_os/test_phase1_integration.py
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import (
    commit_demotion,
    commit_promotion,
)


def _empty_ontology(tmp: Path) -> Path:
    p = tmp / "ontology.json"
    p.write_text(json.dumps({"ontology_version": "test", "ingredients": []}) + "\n")
    return p


def _empty_aliases(tmp: Path) -> Path:
    p = tmp / "variant_aliases.json"
    p.write_text(json.dumps({
        "aliases": {},
        "coverage_os_managed_aliases": [],
    }) + "\n")
    return p


def test_gate_writer_ledger_round_trip_ontology_row(tmp_path):
    """E2E: auto broccoli ontology_row → demote retracts → non_promotable blocks re-gate."""
    ont = _empty_ontology(tmp_path)
    al = _empty_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")

    d = decide_promote(
        candidate_key=key,
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d.action == "auto_promote"
    assert d.rule_id == "closed_form_plant_v1"

    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True, "animal_origin": False},
            "inverse": {"write_kind": "ontology_row", "canonical_name": "broccoli"},
        },
    }
    commit_promotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        rule_id=d.rule_id,
        source="auto",
        auto=True,
    )
    assert led.latest_promoted(key) is not None
    row = next(
        i for i in json.loads(ont.read_text())["ingredients"]
        if i.get("canonical_name") == "broccoli"
    )
    assert row.get("coverage_os_managed") is True

    commit_demotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        reason="sample_audit_fail",
    )
    assert led.latest_promoted(key) is None
    assert not any(
        i.get("canonical_name") == "broccoli"
        for i in json.loads(ont.read_text())["ingredients"]
    )

    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="blocked after demote",
    )
    d2 = decide_promote(
        candidate_key=key,
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d2.action == "rejected"
    assert "non_promotable" in d2.reason


def test_gate_writer_ledger_round_trip_variant_alias(tmp_path):
    """E2E sibling path: auto variant_alias → demote retracts → non_promotable blocks."""
    ont = _empty_ontology(tmp_path)
    al = _empty_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("salt himalayan", "himalayan salt")

    d = decide_promote(
        candidate_key=key,
        candidate_name="salt himalayan",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d.action == "auto_promote"

    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "himalayan salt",
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    commit_promotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        rule_id=d.rule_id,
        source="auto",
        auto=True,
    )
    data = json.loads(al.read_text())
    assert data["aliases"]["salt himalayan"] == "himalayan salt"
    assert "salt himalayan" in data["coverage_os_managed_aliases"]
    assert led.latest_promoted(key) is not None

    commit_demotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        reason="sample_audit_fail",
    )
    assert led.latest_promoted(key) is None
    data = json.loads(al.read_text())
    assert "salt himalayan" not in data["aliases"]
    assert "salt himalayan" not in data.get("coverage_os_managed_aliases", [])

    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="blocked after demote",
    )
    d2 = decide_promote(
        candidate_key=key,
        candidate_name="salt himalayan",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d2.action == "rejected"
    assert "non_promotable" in d2.reason


def test_matrix_emits_chain_for_each_cell():
    rows = run_matrix("sugar, beef", restriction_ids=["hindu_vegetarian", "vegan"])
    assert len(rows) >= 4
    assert all(r["chain"]["restriction_id"] == r["profile"] for r in rows)
    assert all(r["bucket"] == r["chain"]["verdict"] for r in rows)
