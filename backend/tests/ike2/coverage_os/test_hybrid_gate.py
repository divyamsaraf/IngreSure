from core.knowledge.ike2.coverage_os.hybrid_gate import (
    decide_promote,
    has_dual_origin_collision,
    is_umbrella_term,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.truth_anchor import is_compound_umbrella


def _empty_ontology():
    return {"ingredients": []}


def _gelatin_ontology():
    """Mirrors real ontology shape: flat flags + aliases including Gelatine."""
    return {
        "ingredients": [
            {
                "canonical_name": "gelatin",
                "aliases": [
                    "E441", "Gelatine", "Pork Gelatin", "Beef Gelatin",
                    "Fish Gelatin",
                ],
                "animal_origin": True,
                "fish_source": True,
                "plant_origin": False,
            }
        ]
    }


def test_non_promotable_short_circuits(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("roman", "roman")
    led.append_non_promotable(
        candidate_key=key, rule_id="human_reject", source="corpus", reason="junk",
    )
    d = decide_promote(
        candidate_key=key,
        candidate_name="roman",
        flags={"plant_origin": True},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "rejected"
    assert "non_promotable" in d.reason


def test_broccoli_auto_promotes(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("broccoli", "broccoli"),
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "auto_promote"
    assert d.rule_id == "closed_form_plant_v1"


def test_sulphite_goes_human(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("dried apricot", "dried apricot"),
        candidate_name="dried apricot",
        flags={"plant_origin": True, "sulphite_source": True},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_mollusc_species_goes_human(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("snail", "snail"),
        candidate_name="snail",
        flags={"animal_origin": True, "animal_species": "mollusk"},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_beef_goes_human_not_auto(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("beef", "beef"),
        candidate_name="beef",
        flags={"animal_origin": True, "animal_species": "cow"},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_collision_via_alias_not_only_canonical():
    """Positive: plant-looking candidate name hits animal row via alias only."""
    ontology = _gelatin_ontology()
    assert has_dual_origin_collision("gelatine", ontology) is True
    assert has_dual_origin_collision("Gelatine", ontology) is True
    assert has_dual_origin_collision("gelatin", ontology) is True
    assert has_dual_origin_collision("broccoli", ontology) is False


def test_plant_candidate_colliding_alias_routes_human_not_auto(tmp_path):
    """Positive end-to-end: plant-only flags + alias collision → human_approval."""
    led = PromoteLedger(tmp_path / "l.jsonl")
    ontology = _gelatin_ontology()
    d = decide_promote(
        candidate_key=candidate_key("gelatine", "gelatin"),
        candidate_name="gelatine",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=ontology,
    )
    assert d.action == "human_approval"
    assert d.rule_id == "human_dual_origin_collision"
    assert "collision" in d.reason.lower()
    assert "dual" in d.reason.lower()


def test_umbrella_reuses_truth_anchor_compounds(tmp_path):
    """Predicate #5 — shared Tier-1 compounds, not a forked string list."""
    assert is_compound_umbrella("natural flavors") is True
    assert is_compound_umbrella("spices") is True
    assert is_compound_umbrella("broccoli") is False
    assert is_umbrella_term("natural flavors", {"plant_origin": True}) is True
    assert is_umbrella_term("broccoli", {"plant_origin": True}) is False
    assert is_umbrella_term("mystery", {"plant_origin": True, "verdict_cap": "WARN"}) is True
    assert is_umbrella_term("e441", {}) is True

    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("natural flavors", "natural flavors"),
        candidate_name="natural flavors",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"
    assert d.rule_id == "human_umbrella"
    assert "umbrella" in d.reason.lower()
