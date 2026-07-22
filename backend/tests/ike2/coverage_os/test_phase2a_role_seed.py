# backend/tests/ike2/coverage_os/test_phase2a_role_seed.py
import json

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import commit_promotion


def test_seeded_role_visible_to_apply_policies(tmp_path):
    ont = tmp_path / "ontology.json"
    ont.write_text(json.dumps({
        "ingredients": [
            {
                "canonical_name": "almond",
                "plant_origin": True,
                "tree_nut_source": True,
                "animal_origin": False,
            },
            {
                "canonical_name": "yogurt",
                "animal_origin": True,
                "dairy_source": True,
                "plant_origin": False,
            },
        ]
    }))
    aliases = tmp_path / "variant_aliases.json"
    aliases.write_text(json.dumps({"aliases": {}}))
    led = PromoteLedger(tmp_path / "l.jsonl")

    for name, role, flags in (
        ("almond", "plant_mod", {}),
        ("yogurt", "dairy_head", {}),
    ):
        key = candidate_key(name, name)
        d = decide_promote(
            candidate_key=key,
            candidate_name=name,
            flags=flags,
            ledger=led,
            ontology=json.loads(ont.read_text()),
        )
        assert d.action == "human_approval"
        entry = {
            "candidate_key": key,
            "payload": {
                "write_kind": "ontology_row",
                "canonical_name": name,
                "role": role,
                "flags": {},
                "inverse": {
                    "write_kind": "ontology_row",
                    "canonical_name": name,
                    "prior_role": None,
                    "role_patch_only": True,
                },
            },
        }
        commit_promotion(
            entry,
            led,
            ontology_path=ont,
            aliases_path=aliases,
            rule_id=d.rule_id,
            source="test",
            auto=False,
            reviewer_id="test",
            approval_rationale="test seed",
            candidate_key=key,
        )

    rows = json.loads(ont.read_text())["ingredients"]
    roles = build_role_index(rows)
    flags = {
        "yogurt": {"dairy_source": True, "animal_origin": True},
        "almond": {"plant_origin": True, "tree_nut_source": True},
    }
    r = apply_policies(
        "almond yogurt",
        role_index=roles,
        lookup_flags=lambda t: flags.get(t),
    )
    assert "plant_mod" in r.policy_fired
    assert "yogurt" not in r.atoms
