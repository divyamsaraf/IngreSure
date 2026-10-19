# backend/tests/ike2/coverage_os/induction/test_submit.py
from __future__ import annotations

import ast
import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.induction.submit import submit_induced
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


def test_submit_force_human_even_when_gate_would_auto(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    aliases_path = tmp_path / "variant_aliases.json"
    ontology_path.write_text(
        json.dumps({"ingredients": [{"canonical_name": "broccoli", "plant_origin": True}]}),
        encoding="utf-8",
    )
    aliases_path.write_text(json.dumps({"aliases": {}}), encoding="utf-8")
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))

    cand = InductionCandidate(
        proposal_kind="variant_alias",
        raw="broccoli florets",
        canonical="broccoli",
        role=None,
        frequency=5,
        miss_class="M4_morphology",
        safety_class="plant_closed",
        provenance={"rule": "unique_head"},
        flags={"plant_origin": True},
    )

    row = submit_induced(
        cand,
        ledger=ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        ontology=ontology,
        reviewer_id="tester",
        approval_rationale="accept plant alias",
        decision="accept",
    )
    assert row is not None
    assert row["auto"] is False
    assert row["reviewer_id"] == "tester"
    assert row["payload"]["induction"]["safety_class"] == "plant_closed"


def test_submit_reject_records_non_promotable_with_induction_payload(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    aliases_path = tmp_path / "variant_aliases.json"
    ontology_path.write_text(json.dumps({"ingredients": []}), encoding="utf-8")
    aliases_path.write_text(json.dumps({"aliases": {}}), encoding="utf-8")
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")

    cand = InductionCandidate(
        proposal_kind="variant_alias",
        raw="junk",
        canonical="junk",
        role=None,
        frequency=1,
        miss_class="M1_absent",
        safety_class="role_only",
        provenance={"rule": "test"},
        flags={},
    )
    row = submit_induced(
        cand,
        ledger=ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        ontology={"ingredients": []},
        reviewer_id="tester",
        approval_rationale="n/a",
        decision="reject",
    )
    assert row is not None
    assert row["kind"] == "confirmed_non_promotable"
    assert row["source"] == "phase2b_induction"
    assert row["payload"]["induction"]["safety_class"] == "role_only"
    assert json.loads(aliases_path.read_text(encoding="utf-8")) == {"aliases": {}}


def test_submit_has_no_auto_true_call_site():
    from core.knowledge.ike2.coverage_os.induction import submit as submit_mod

    tree = ast.parse(Path(submit_mod.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords or []:
                if kw.arg == "auto" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    raise AssertionError("submit must not pass auto=True")
