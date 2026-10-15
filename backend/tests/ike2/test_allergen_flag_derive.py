"""Identity-derived allergen families added after Item 7 stem scan (2026-10-07)."""
from core.knowledge.ike2.flag_derive import derive_identity_flags


def test_gluten_ancient_grains_and_barley_forms():
    for name in (
        "einkorn",
        "khorasan",
        "barley groats",
        "spelt flour",
        "rye starch",
        "rava",
    ):
        assert derive_identity_flags(name, {})["gluten_source"] is True, name
    assert derive_identity_flags("buckwheat", {}).get("gluten_source") is not True
    # Idli rava is rice grits, not wheat semolina.
    assert derive_identity_flags("idli rava", {}).get("gluten_source") is not True


def test_lupin_and_tahini_and_shellfish_labels():
    assert derive_identity_flags("lupini beans", {})["lupin_source"] is True
    assert derive_identity_flags("tahini paste", {})["sesame_source"] is True
    assert derive_identity_flags("crustaceans", {})["shellfish_source"] is True
    assert derive_identity_flags("mollusks", {})["shellfish_source"] is True


def test_dairy_with_plant_milk_exclusions():
    assert derive_identity_flags("whey powder", {})["dairy_source"] is True
    assert derive_identity_flags("buffalo milk fat", {})["dairy_source"] is True
    assert derive_identity_flags("hemp milk", {}).get("dairy_source") is not True
    assert derive_identity_flags("kokum butter", {}).get("dairy_source") is not True
    assert derive_identity_flags("milk fish", {}).get("dairy_source") is not True


def test_mustard_and_celery_with_exclusions():
    assert derive_identity_flags("mustard seeds", {})["mustard_source"] is True
    assert derive_identity_flags("mustard greens", {}).get("mustard_source") is not True
    assert derive_identity_flags("mustard oil", {}).get("mustard_source") is not True
    assert derive_identity_flags("celery stalk", {})["celery_source"] is True


def test_free_from_negation_suppresses_family_derive():
    """Free-from / contains-no claims must not fire identity Avoid on the stem."""
    cases = (
        ("gluten free pasta", "gluten_source"),
        ("gluten-free bread", "gluten_source"),
        ("free from gluten", "gluten_source"),
        ("dairy free cheese", "dairy_source"),
        ("dairy-free mayonnaise", "dairy_source"),
        ("egg free pasta", "egg_source"),
        ("egg-free mayonnaise", "egg_source"),
        ("nut free bread", "tree_nut_source"),
        ("peanut free bread", "peanut_source"),
        ("sulphite free pasta", "sulphite_source"),
        ("sulfite-free bread", "sulphite_source"),
        ("no added sulphites", "sulphite_source"),
        ("contains no peanuts", "peanut_source"),
    )
    for name, flag in cases:
        got = derive_identity_flags(name, {})
        assert got.get(flag) is not True, f"{name!r} still set {flag}"
    # Positive controls still fire.
    assert derive_identity_flags("gluten", {})["gluten_source"] is True
    assert derive_identity_flags("sodium sulphite", {})["sulphite_source"] is True
    assert derive_identity_flags("peanuts", {})["peanut_source"] is True
