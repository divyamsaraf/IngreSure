import pytest

from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.truth_anchor import lookup


def _unique_canonicals():
    return {fact.canonical_name for fact in ta._ANCHORS.values()}


def test_gelatin_is_animal_and_locked():
    fact = lookup("gelatin")
    assert fact is not None
    assert fact.flags["animal_origin"] is True
    assert fact.knowledge_state == "LOCKED"


def test_carmine_e120_is_insect():
    for key in ("carmine", "e120", "cochineal"):
        fact = lookup(key)
        assert fact is not None, key
        assert fact.flags["insect_derived"] is True


def test_unknown_key_returns_none():
    assert lookup("totally_unknown_thing_xyz") is None


def test_all_hand_anchors_are_locked_or_compound():
    compound = {
        "natural flavors",
        "artificial flavors",
        "flavor",
        "spices",
        "enzymes",
        "preservatives",
        "colors",
    }
    for fact in ta._ANCHORS.values():
        if fact.canonical_name in compound:
            assert fact.knowledge_state == "VERIFIED"
            assert fact.flags.get("verdict_cap") == "WARN"
        else:
            assert fact.knowledge_state == "LOCKED"


def test_canonical_entry_count_toward_spec_target():
    # Spec calls for ~80 safety-critical facts; allow headroom for alias growth.
    assert len(_unique_canonicals()) >= 75


@pytest.mark.parametrize(
    "key,flag",
    [
        ("peanut", "peanut_source"),
        ("almond", "tree_nut_source"),
        ("walnut", "tree_nut_source"),
        ("cashew", "tree_nut_source"),
        ("milk", "dairy_source"),
        ("whey", "dairy_source"),
        ("egg", "egg_source"),
        ("albumin", "egg_source"),
        ("wheat", "gluten_source"),
        ("gluten", "gluten_source"),
        ("soy", "soy_source"),
        ("tofu", "soy_source"),
        ("sesame", "sesame_source"),
        ("mustard", "mustard_source"),
        ("celery", "celery_source"),
        ("lupin", "lupin_source"),
        ("sulfite", "sulphite_source"),
        ("fish", "fish_source"),
        ("anchovy", "fish_source"),
        ("shrimp", "shellfish_source"),
        ("crab", "shellfish_source"),
        ("shellfish", "shellfish_source"),
    ],
)
def test_common_allergen_flags(key, flag):
    fact = lookup(key)
    assert fact is not None, key
    assert fact.flags[flag] is True


@pytest.mark.parametrize(
    "key,species",
    [
        ("pork", "pig"),
        ("bacon", "pig"),
        ("ham", "pig"),
        ("lard", "pig"),
        ("beef", "cow"),
        ("veal", "cow"),
        ("tallow", "cow"),
    ],
)
def test_meat_species_cases(key, species):
    fact = lookup(key)
    assert fact is not None, key
    assert fact.flags["animal_origin"] is True
    assert fact.flags["animal_species"] == species


@pytest.mark.parametrize(
    "key",
    [
        "e441",
        "e631",
        "e901",
        "e904",
        "e966",
        "beeswax",
        "lanolin",
        "l-cysteine",
        "rennet",
        "collagen",
        "honey",
        "castoreum",
    ],
)
def test_animal_derived_additive_keys(key):
    fact = lookup(key)
    assert fact is not None, key
    assert fact.flags["animal_origin"] is True


@pytest.mark.parametrize(
    "key",
    ["wine", "beer", "vodka", "rum", "whiskey", "vanilla extract"],
)
def test_alcohol_source_keys(key):
    fact = lookup(key)
    assert fact is not None, key
    assert fact.flags.get("alcohol_content", 0) > 0 or fact.flags.get("alcohol_role") == "ingredient"


@pytest.mark.parametrize(
    "key,flag",
    [
        ("onion", "onion_source"),
        ("garlic", "garlic_source"),
        ("shallot", "onion_source"),
        ("leek", "onion_source"),
    ],
)
def test_jain_relevant_roots(key, flag):
    fact = lookup(key)
    assert fact is not None, key
    assert fact.flags[flag] is True


def test_lard_and_tallow_are_distinct_species():
    assert lookup("lard").flags["animal_species"] == "pig"
    assert lookup("tallow").flags["animal_species"] == "cow"


@pytest.mark.parametrize("key", ["sugar", "cane sugar", "beet sugar", "flour", "chicken", "potato"])
def test_tier1_core_present(key):
    assert lookup(key) is not None


def test_sugar_plant_safe_flags():
    f = lookup("sugar")
    assert f.flags.get("animal_origin") is False
    assert f.flags.get("plant_origin") is True
    assert "bone_char" not in str(f.flags.get("uncertainty_flags") or [])


def test_chicken_has_species():
    f = lookup("chicken")
    assert f.flags.get("animal_origin") is True
    assert f.flags.get("animal_species") == "chicken"


def test_potato_jain_friendly_flags():
    f = lookup("potato")
    assert f.flags.get("root_vegetable") is True
    assert f.flags.get("plant_origin") is True


@pytest.mark.parametrize("key", ["elephant foot yam", "taro root"])
def test_regional_root_vegetables_resolve_offline(key):
    # Regional parsing rewrites "yam"/"suran" -> "elephant foot yam" and
    # "arbi"/"taro" -> "taro root"; the canonicals must be Tier-1 root
    # vegetables so Jain avoids them without ever reaching Supabase.
    f = lookup(key)
    assert f is not None, key
    assert f.flags.get("root_vegetable") is True
    assert f.flags.get("plant_origin") is True


@pytest.mark.parametrize("key", ["collagen", "rennet"])
def test_species_unknown_animal_additives(key):
    f = lookup(key)
    assert f is not None
    assert f.flags.get("animal_origin") is True
    assert "animal_species" not in f.flags
