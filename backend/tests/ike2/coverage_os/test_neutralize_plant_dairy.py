# backend/tests/ike2/coverage_os/test_neutralize_plant_dairy.py
from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index


def _flags_lookup(table):
    def lookup(token: str):
        return table.get(token.lower().strip())
    return lookup


def test_plant_mod_almond_yogurt_both_orders():
    roles = {"almond": "plant_mod", "yogurt": "dairy_head"}
    flags = {
        "yogurt": {"dairy_source": True, "animal_origin": True},
        "almond": {"plant_origin": True, "tree_nut_source": True},
    }
    for phrase in ("almond yogurt", "yogurt almond"):
        r = apply_policies(phrase, role_index=roles, lookup_flags=_flags_lookup(flags))
        assert r.atoms[0] == phrase
        assert "almond" in r.atoms
        assert "yogurt" not in r.atoms  # bare dairy never emitted
        assert r.derived_from["almond"] == phrase
        assert "plant_mod" in r.policy_fired


def test_plant_mod_wins_over_dairy_head_on_plant_yogurt():
    roles = {"plant": "plant_mod", "yogurt": "dairy_head"}
    flags = {"yogurt": {"dairy_source": True, "animal_origin": True}}
    r = apply_policies(
        "plant yogurt", role_index=roles, lookup_flags=_flags_lookup(flags),
    )
    assert "plant_mod" in r.policy_fired
    assert "dairy_head" not in r.policy_fired
    assert "yogurt" not in r.atoms


def test_dairy_head_yogurt_goat_both_orders_no_bare_goat_dairy_tear():
    roles = {"yogurt": "dairy_head"}
    flags = {
        "yogurt": {"dairy_source": True, "animal_origin": True},
        "goat": {"animal_origin": True, "animal_species": "goat"},
    }
    for phrase in ("yogurt goat", "goat yogurt"):
        r = apply_policies(phrase, role_index=roles, lookup_flags=_flags_lookup(flags))
        assert r.atoms == [phrase]
        assert "dairy_head" in r.policy_fired
        assert "goat" not in r.atoms


def test_plant_mod_partner_via_is_animalish_without_dairy_head_role():
    """Partner need not have role=dairy_head — flags via is_animalish suffice."""
    roles = {"coconut": "plant_mod"}  # milk has no role
    flags = {"milk": {"dairy_source": True, "animal_origin": True}}
    r = apply_policies(
        "coconut milk", role_index=roles, lookup_flags=_flags_lookup(flags),
    )
    assert "plant_mod" in r.policy_fired
    assert "milk" not in r.atoms
    assert "coconut" in r.atoms
    assert r.derived_from["coconut"] == "coconut milk"


def test_build_role_index_reads_role_field():
    idx = build_role_index([
        {"canonical_name": "Almond", "role": "plant_mod"},
        {"canonical_name": "yogurt", "role": "dairy_head", "aliases": ["yoghurt"]},
    ])
    assert idx["almond"] == "plant_mod"
    assert idx["yogurt"] == "dairy_head"
    assert idx["yoghurt"] == "dairy_head"
