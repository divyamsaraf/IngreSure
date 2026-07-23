from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import A1_DANGEROUS


def _empty_ledger(tmp_path):
    return PromoteLedger(tmp_path / "ledger.jsonl")


@pytest.mark.parametrize(
    "name,flags,ontology,expected_class,expected_rule_id",
    [
        ("soy lecithin", {"soy_source": True}, {"ingredients": []}, "allergen_adjacent", "human_allergen_adjacent"),
        ("gelatin", {"animal_origin": True}, {"ingredients": []}, "animalish", "human_animal_derived"),
        (
            "ghee",
            {},
            {"ingredients": [{"canonical_name": "ghee", "animal_origin": True, "dairy_source": True}]},
            "dual_origin",
            "human_dual_origin_collision",
        ),
        ("natural flavors", {"verdict_cap": "WARN"}, {"ingredients": []}, "umbrella", "human_umbrella"),
        ("broccoli", {"plant_origin": True}, {"ingredients": []}, "plant_closed", "closed_form_plant_v1"),
        ("mystery token", {}, {"ingredients": []}, "role_only", "human_fail_closed"),
    ],
)
def test_safety_class_aligns_with_decide_promote(
    tmp_path, name, flags, ontology, expected_class, expected_rule_id
):
    sc = assign_safety_class(candidate_name=name, flags=flags, ontology=ontology)
    assert sc == expected_class
    decision = decide_promote(
        candidate_key=f"{name}=>{name}",
        candidate_name=name,
        flags=flags,
        ledger=_empty_ledger(tmp_path),
        ontology=ontology,
    )
    assert decision.rule_id == expected_rule_id
    if expected_class in A1_DANGEROUS:
        assert decision.action == "human_approval"
    if expected_class == "plant_closed":
        assert decision.action == "auto_promote"


def test_assign_safety_class_calls_is_animalish_not_inline(monkeypatch):
    """LCT-1: prove literal call to deny_lists helper, not re-derived flags."""
    import core.knowledge.ike2.coverage_os.induction.safety_class as mod

    calls: list = []

    def spy(flags):
        calls.append(dict(flags or {}))
        return True

    monkeypatch.setattr(mod, "is_animalish", spy)
    monkeypatch.setattr(mod, "is_allergen_adjacent", lambda f: False)
    out = assign_safety_class(
        candidate_name="x",
        flags={"animal_origin": True},
        ontology={"ingredients": []},
    )
    assert out == "animalish"
    assert calls, "is_animalish was not called"


def test_safety_class_module_has_no_local_animal_frozenset():
    import core.knowledge.ike2.coverage_os.induction.safety_class as sc_mod

    path = Path(sc_mod.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and "ANIMAL" in t.id.upper():
                    pytest.fail(f"forbidden local constant {t.id}")
