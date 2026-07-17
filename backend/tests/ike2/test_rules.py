from pathlib import Path
from types import SimpleNamespace

from core.knowledge.ike2 import rules
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict

_SEED_SQL = (
    Path(__file__).resolve().parents[3]
    / "supabase/migrations/20260617000000_ike2_seed_restriction_rules.sql"
)


def _resolved(**flags):
    base = {
        "canonical_name": "x",
        "knowledge_state": "VERIFIED",
        "trusted": True,
        "verdict_cap": None,
        "alcohol_role": flags.get("alcohol_role", "none"),
        "trace": False,
    }
    return SimpleNamespace(flags=flags, **base)


def _profile(**restrictions):
    return SimpleNamespace(restrictions=restrictions)


def test_seed_covers_exactly_the_supported_restrictions():
    # Dropping (or sneaking in) a seed row is caught here.
    expected = {
        "peanut_allergy", "tree_nut_allergy", "soy_allergy", "sesame_allergy",
        "fish_allergy", "shellfish_allergy", "mustard_allergy", "lupin_allergy",
        "celery_allergy", "onion_allergy", "garlic_allergy",
        "gluten_free", "celiac_strict", "lactose_free", "dairy_free", "egg_free",
        "sulfite_sensitive",
        "vegan", "no_insect_derived", "no_onion", "no_garlic", "no_alcohol",
        "halal", "kosher", "hindu_vegetarian", "hindu_non_vegetarian", "jain",
        "vegetarian", "lacto_vegetarian", "ovo_vegetarian", "pescatarian",
    }
    assert rules.SUPPORTED_RESTRICTIONS == expected
    covered = {r.restriction for r in rules.seeded_rules()}
    for restriction in rules.SUPPORTED_RESTRICTIONS:
        assert restriction in covered


def test_every_flag_rule_targets_a_real_group_column():
    # A typo'd trigger_flag would silently never fire -> false-SAFE. Guard it.
    for rule in rules.seeded_rules():
        if rule.kind == "flag":
            assert rule.trigger_flag in rules.VALID_FLAG_COLUMNS


def test_alcohol_rule_is_kind_alcohol():
    alcohol = [r for r in rules.seeded_rules() if r.restriction == "no_alcohol"]
    assert len(alcohol) == 1
    assert alcohol[0].kind == "alcohol"
    assert alcohol[0].trigger_flag is None


def test_seed_sql_covers_rule_seed():
    # Drift guard: the live-DB seed must contain every in-code rule.
    sql = _SEED_SQL.read_text()
    for row in rules.RULE_SEED:
        assert f"'{row['category']}'" in sql
        assert f"'{row['field']}'" in sql


def test_seeded_rules_flag_a_peanut_ingredient():
    r = _resolved(peanut_source=True)
    result = evaluate([r], _profile(peanut_allergy="medical"), rules.seeded_rules())
    assert result.verdict != Verdict.SAFE


def test_seeded_rules_pass_a_clean_ingredient():
    r = _resolved(animal_origin=False)
    result = evaluate([r], _profile(vegan="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE


# ---- multi-field religious / lifestyle rules --------------------------------
def test_halal_fails_on_pig():
    r = _resolved(animal_species="pig", animal_origin=True, insect_derived=False)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_halal_fails_on_unspecified_gelatin():
    """Generic gelatin lists porcine among possible sources; must not be halal-safe."""
    r = _resolved(
        canonical_name="gelatin",
        animal_species="bovine/porcine/fish depending on source",
        animal_origin=True,
        insect_derived=False,
    )
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_kosher_fails_on_unspecified_gelatin():
    r = _resolved(
        canonical_name="gelatin",
        animal_species="bovine/porcine/fish depending on source",
        animal_origin=True,
        insect_derived=False,
    )
    result = evaluate([r], _profile(kosher="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_halal_fails_on_alcohol_content():
    r = _resolved(alcohol_content=12.0, animal_origin=False)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_kosher_fails_on_shellfish_species():
    r = _resolved(animal_species="shellfish", animal_origin=True, fish_source=True)
    result = evaluate([r], _profile(kosher="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_jain_fails_on_root_vegetable():
    r = _resolved(root_vegetable=True, animal_origin=False)
    result = evaluate([r], _profile(jain="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_jain_fermented_warns_not_fails():
    r = _resolved(
        fermented=True, animal_origin=False, root_vegetable=False,
        onion_source=False, garlic_source=False, fungal=False,
    )
    result = evaluate([r], _profile(jain="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.WARN


def test_vegetarian_fails_on_fish_via_meat_fish_derived():
    r = _resolved(animal_origin=True, fish_source=True, dairy_source=False, egg_source=False)
    result = evaluate([r], _profile(vegetarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_lacto_vegetarian_allows_dairy_blocks_egg():
    dairy_ok = _resolved(animal_origin=True, dairy_source=True, egg_source=False)
    assert evaluate([dairy_ok], _profile(lacto_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.SAFE
    egg_bad = _resolved(animal_origin=True, egg_source=True, dairy_source=False)
    assert evaluate([egg_bad], _profile(lacto_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.FAIL


def test_ovo_vegetarian_allows_egg_blocks_dairy():
    egg_ok = _resolved(animal_origin=True, egg_source=True, dairy_source=False)
    assert evaluate([egg_ok], _profile(ovo_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.SAFE
    dairy_bad = _resolved(animal_origin=True, dairy_source=True, egg_source=False)
    assert evaluate([dairy_bad], _profile(ovo_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.FAIL


def test_pescatarian_fails_on_chicken():
    r = _resolved(animal_species="chicken", animal_origin=True)
    result = evaluate([r], _profile(pescatarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_pescatarian_allows_fish():
    r = _resolved(animal_species="fish", animal_origin=True, fish_source=True)
    result = evaluate([r], _profile(pescatarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE


def test_unknown_species_with_animal_origin_is_not_safe_for_halal():
    r = _resolved(animal_origin=True, animal_species=None)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict != Verdict.SAFE


def test_halal_covered_no_longer_uncertain():
    r = _resolved(animal_origin=False, insect_derived=False, alcohol_content=None)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE
    assert not any("uncovered_restriction" in c for c in result.caution_reasons)


def test_load_rules_falls_back_to_seed_when_db_unreachable(monkeypatch):
    """Configured Supabase that is down must not break IKE-2 (fail-closed seed)."""

    class _BrokenTable:
        def select(self, *_args, **_kwargs):
            return self

        def execute(self):
            raise ConnectionError("connection refused")

    class _BrokenClient:
        def table(self, _name):
            return _BrokenTable()

    monkeypatch.setattr(rules, "seeded_rules", rules.seeded_rules)
    loaded = rules.load_rules(client=_BrokenClient())
    assert len(loaded) == len(rules.seeded_rules())
    assert {r.restriction for r in loaded} == rules.SUPPORTED_RESTRICTIONS
