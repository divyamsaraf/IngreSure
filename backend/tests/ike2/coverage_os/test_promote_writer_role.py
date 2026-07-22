# backend/tests/ike2/coverage_os/test_promote_writer_role.py
import json

from core.knowledge.ike2.coverage_os.promote_writer import apply_promotion, retract_promotion


def test_role_patch_on_existing_non_managed_row(tmp_path):
    ont = tmp_path / "ontology.json"
    ont.write_text(json.dumps({
        "ingredients": [{
            "canonical_name": "yogurt",
            "animal_origin": True,
            "dairy_source": True,
            "plant_origin": False,
        }]
    }))
    aliases = tmp_path / "variant_aliases.json"
    aliases.write_text(json.dumps({"aliases": {}}))
    entry = {
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "yogurt",
            "role": "dairy_head",
            "flags": {},
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": "yogurt",
                "prior_role": None,
                "role_patch_only": True,
            },
        }
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=aliases)
    row = json.loads(ont.read_text())["ingredients"][0]
    assert row["role"] == "dairy_head"
    assert row["dairy_source"] is True  # untouched
    assert row.get("coverage_os_role_managed") is True
    assert row.get("coverage_os_managed") is not True

    retract_promotion(entry, ontology_path=ont, aliases_path=aliases)
    row2 = json.loads(ont.read_text())["ingredients"][0]
    assert "role" not in row2 or row2.get("role") in (None, "")
    assert row2.get("coverage_os_role_managed") is not True
