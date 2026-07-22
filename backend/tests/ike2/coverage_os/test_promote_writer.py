import json
from pathlib import Path
from unittest.mock import patch

from core.knowledge.ike2.coverage_os.promote_writer import (
    apply_promotion,
    retract_promotion,
    commit_promotion,
    commit_demotion,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def _base_ontology(tmp: Path) -> Path:
    p = tmp / "ontology.json"
    p.write_text(json.dumps({"ontology_version": "test", "ingredients": []}) + "\n")
    return p


def _base_aliases(tmp: Path) -> Path:
    p = tmp / "variant_aliases.json"
    p.write_text(json.dumps({
        "aliases": {},
        "coverage_os_managed_aliases": [],
    }) + "\n")
    return p


def test_apply_and_retract_variant_alias(tmp_path):
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "himalayan salt",
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=al)
    data = json.loads(al.read_text())
    assert data["aliases"]["salt himalayan"] == "himalayan salt"
    assert "salt himalayan" in data["coverage_os_managed_aliases"]
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    data = json.loads(al.read_text())
    assert "salt himalayan" not in data["aliases"]
    assert "salt himalayan" not in data["coverage_os_managed_aliases"]


def test_apply_and_retract_ontology_row(tmp_path):
    """Symmetric path — most Coverage OS candidates are new ingredient facts."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True, "animal_origin": False},
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": "broccoli",
            },
        },
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=al)
    ingredients = json.loads(ont.read_text())["ingredients"]
    row = next(i for i in ingredients if i.get("canonical_name") == "broccoli")
    assert row["flags"]["plant_origin"] is True
    assert row.get("coverage_os_managed") is True
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    ingredients = json.loads(ont.read_text())["ingredients"]
    assert not any(i.get("canonical_name") == "broccoli" for i in ingredients)


def test_write_failure_leaves_ledger_pending(tmp_path):
    """Write fails → no promoted ledger row (never mark promoted that was not written)."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("broccoli", "broccoli")
    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True},
            "inverse": {"write_kind": "ontology_row", "canonical_name": "broccoli"},
        },
    }
    with patch(
        "core.knowledge.ike2.coverage_os.promote_writer.apply_promotion",
        side_effect=OSError("disk full"),
    ):
        try:
            commit_promotion(
                entry,
                led,
                ontology_path=ont,
                aliases_path=al,
                rule_id="closed_form_plant_v1",
                source="test",
            )
            assert False, "expected OSError"
        except OSError:
            pass
    assert led.latest_promoted(key) is None


def test_retract_failure_leaves_promotion_active(tmp_path):
    """Retract fails → ledger still shows active promote (never claim demote without disk)."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("broccoli", "broccoli")
    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True},
            "inverse": {"write_kind": "ontology_row", "canonical_name": "broccoli"},
        },
    }
    commit_promotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        rule_id="closed_form_plant_v1",
        source="test",
    )
    assert led.latest_promoted(key) is not None
    with patch(
        "core.knowledge.ike2.coverage_os.promote_writer.retract_promotion",
        side_effect=OSError("disk full"),
    ):
        try:
            commit_demotion(
                entry,
                led,
                ontology_path=ont,
                aliases_path=al,
                reason="sample_audit_fail",
            )
            assert False, "expected OSError"
        except OSError:
            pass
    assert led.latest_promoted(key) is not None
    assert any(
        i.get("canonical_name") == "broccoli"
        for i in json.loads(ont.read_text())["ingredients"]
    )


def test_refuse_overwrite_and_retract_unmanaged_alias(tmp_path):
    """Parity with ontology coverage_os_managed — hand-authored aliases are sacred."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    al.write_text(json.dumps({
        "aliases": {"salt himalayan": "himalayan salt"},
        "coverage_os_managed_aliases": [],
    }) + "\n")
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "table salt",
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    try:
        apply_promotion(entry, ontology_path=ont, aliases_path=al)
        assert False, "expected ValueError on unmanaged overwrite"
    except ValueError as e:
        assert "non-coverage_os_managed" in str(e)
    aliases = json.loads(al.read_text())["aliases"]
    assert aliases["salt himalayan"] == "himalayan salt"
    try:
        retract_promotion(entry, ontology_path=ont, aliases_path=al)
        assert False, "expected ValueError on unmanaged retract"
    except ValueError as e:
        assert "non-coverage_os_managed" in str(e)
    aliases = json.loads(al.read_text())["aliases"]
    assert aliases["salt himalayan"] == "himalayan salt"
