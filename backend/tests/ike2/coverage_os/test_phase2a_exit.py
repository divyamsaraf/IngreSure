# backend/tests/ike2/coverage_os/test_phase2a_exit.py
import json

from core.compound_expansion import expand_compounds
from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import (
    commit_demotion,
    commit_promotion,
)


def test_role_round_trip_promote_apply_demote(tmp_path):
    ont = tmp_path / "ontology.json"
    ont.write_text(json.dumps({
        "ingredients": [{
            "canonical_name": "almond",
            "plant_origin": True,
            "tree_nut_source": True,
        }]
    }))
    aliases = tmp_path / "variant_aliases.json"
    aliases.write_text(json.dumps({"aliases": {}}))
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("almond", "almond")
    d = decide_promote(
        candidate_key=key,
        candidate_name="almond",
        flags={},
        ledger=led,
        ontology=json.loads(ont.read_text()),
    )
    assert d.action == "human_approval"
    entry = {
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "almond",
            "role": "plant_mod",
            "flags": {},
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": "almond",
                "prior_role": None,
                "role_patch_only": True,
            },
        },
    }
    commit_promotion(
        entry, led,
        ontology_path=ont, aliases_path=aliases,
        rule_id=d.rule_id, source="test", auto=False,
        reviewer_id="t", approval_rationale="t", candidate_key=key,
    )
    roles = build_role_index(json.loads(ont.read_text())["ingredients"])
    assert roles["almond"] == "plant_mod"
    r = apply_policies(
        "almond yogurt",
        role_index={**roles, "yogurt": "dairy_head"},
        lookup_flags=lambda t: {
            "yogurt": {"dairy_source": True, "animal_origin": True},
        }.get(t),
    )
    assert "plant_mod" in r.policy_fired

    commit_demotion(
        entry, led,
        ontology_path=ont, aliases_path=aliases,
        reason="test demote", candidate_key=key,
    )
    roles2 = build_role_index(json.loads(ont.read_text())["ingredients"])
    assert "almond" not in roles2 or roles2.get("almond") != "plant_mod"


def test_matrix_smoke_no_new_false_safe_on_culinary(tmp_path):
    """Lightweight smoke: culinary-kept vinegar must not expand to wine."""
    expanded, _, _ = expand_compounds(
        ["wine vinegar", "soy lecithin"],
        role_index={"vinegar": "culinary_keep", "lecithin": "culinary_keep"},
    )
    lows = [e.lower() for e in expanded]
    assert "wine" not in lows
    assert "soy" not in lows
    assert "wine vinegar" in lows
    assert "soy lecithin" in lows
