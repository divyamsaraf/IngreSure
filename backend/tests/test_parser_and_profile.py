"""
Unit tests: flatten_ingredients (parentheses, processed foods), UserProfile merge, minor ingredients.
Run from backend: python -m pytest tests/test_parser_and_profile.py -v
"""
import json
import tempfile
import pytest
from pathlib import Path


def test_flatten_ingredients_parentheses():
    """Parser splits parentheses and commas inside them."""
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients("Enriched Bleached Wheat Flour (Bleached Wheat Flour, Niacin, Folic Acid)")
    assert "bleached wheat flour" in out
    assert "niacin" in out
    assert "folic acid" in out


def test_flatten_ingredients_category_expand():
    """X (A, B, C) expands when X is a known category: vegetable oil (sunflower, canola) -> sunflower oil, canola oil."""
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients("vegetable oil (sunflower, canola), salt")
    assert "sunflower oil" in out
    assert "canola oil" in out
    assert "salt" in out


def test_flatten_ingredients_processed_food():
    """Processed foods map to base ingredients (e.g. potato chips -> potato, vegetable oil, salt)."""
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients("potato chips")
    assert "potato" in out
    assert "vegetable oil" in out
    assert "salt" in out


def test_flatten_ingredients_potato_chips_uppercase():
    """Case-insensitive processed food match."""
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients("Potato Chips")
    assert "potato" in out


def test_normalize_ingredient_key_variant():
    """Known variants (e.g. inglass -> isinglass) are applied for lookup."""
    from core.normalization.normalizer import normalize_ingredient_key
    assert normalize_ingredient_key("inglass") == "isinglass"
    assert normalize_ingredient_key("Isinglass") == "isinglass"
    assert normalize_ingredient_key("fish gelatin") == "fish_gelatin"
    assert normalize_ingredient_key("  castoreum  ") == "castoreum"


def test_flatten_ingredients_enriched_wheat_flour_full():
    """Flatten full enriched flour string with parentheses and commas inside."""
    from core.normalization.parser import flatten_ingredients
    raw = "Enriched Bleached Wheat Flour (Bleached Wheat Flour, Niacin, Reduced Iron, Thiamine Mononitrate, Riboflavin, Folic Acid)"
    out = flatten_ingredients(raw)
    assert "bleached wheat flour" in out
    assert "niacin" in out
    assert "folic acid" in out
    assert "reduced iron" in out
    assert "riboflavin" in out
    # Should have multiple atoms (parentheses split)
    assert len(out) >= 5


def test_flatten_strips_percentage_only_atoms():
    """Quantity percents are not ingredients (Item 44 splitter)."""
    from core.normalization.parser import flatten_ingredients

    out = flatten_ingredients("farine de blé, sucre, 4%, huile de colza, sugar 8%")
    assert "4%" not in out
    assert "8%" not in out
    assert "sugar 8%" not in out
    assert "sucre" in out
    assert "sugar" in out
    assert "huile de colza" in out


def test_flatten_keeps_name_when_paren_is_composition_percent():
    """Composition % must not replace the ingredient (false-SAFE root cause)."""
    from core.normalization.parser import flatten_ingredients

    out = flatten_ingredients(
        "PEANUTS (49.5%), honey, dark chocolate (12%) (cocoa mass, cane sugar, cocoa butter), "
        "SOYA crispies (10.5%), desiccated coconut (7.5%), rice syrup, salt."
    )
    assert "peanut" in out or "peanuts" in out
    assert "honey" in out
    assert "salt" in out
    assert "49.5%" not in out
    assert "12%" not in out
    # dark chocolate expands or keeps cocoa constituents
    assert any(x in out for x in ("cocoa", "cocoa mass", "dark chocolate", "cane sugar"))


@pytest.mark.parametrize(
    "raw,must_keep",
    [
        ("peanuts (49.5%)", "peanut"),
        ("peanuts (49,5 %)", "peanut"),
        ("wheat flour (min. 62%)", "wheat flour"),
        ("milk 3.5%", "milk"),
        ("peanuts 49.5%", "peanut"),
    ],
)
def test_flatten_composition_percent_goldens(raw, must_keep):
    """Hazard/identity tokens must survive composition-percent noise."""
    from core.normalization.parser import flatten_ingredients

    out = flatten_ingredients(raw)
    assert must_keep in out, (raw, out)
    assert not any("%" in a for a in out)
    assert "min" not in out


def test_truth_anchor_class_staple_oils_and_water_variants():
    """Item 44 class-level staple aliases resolve at L1."""
    from core.knowledge.ike2 import resolution_cache as cache
    from core.knowledge.ike2.resolver import resolve

    for atom, canonical in (
        ("rapeseed oil", "vegetable oil"),
        ("sunflower oil", "vegetable oil"),
        ("edible vegetable oil", "vegetable oil"),
        ("filtered water", "water"),
        ("iodised salt", "salt"),
        ("lodised salt", "salt"),
        ("wheatberries", "wheat"),
        ("vitamin b6", "vitamin b6"),
        ("vitamin d3", "vitamin d"),
    ):
        cache.clear()
        r = resolve(atom, None)
        assert r.resolution_layer.startswith("L1"), (atom, r.resolution_layer)
        assert r.trusted is True
        assert r.group is not None
        assert r.group.canonical_name == canonical


def test_flatten_strips_contains_and_may_contain_markers():
    """Allergen declarations are not a single opaque atom."""
    from core.normalization.parser import flatten_ingredients

    out = flatten_ingredients("Ingredients: wheat flour. Contains wheat.")
    assert "contains wheat" not in out
    assert "wheat" in out
    assert "wheat flour" in out

    out2 = flatten_ingredients("milk, salt. May contain peanuts.")
    assert "may contain peanuts" not in out2
    assert "peanut" in out2 or "peanuts" in out2
    assert "milk" in out2


def test_flatten_keeps_category_expand_with_cleaned_atoms():
    """Percent / contains cleanup must not break vegetable oil (A, B) expand."""
    from core.normalization.parser import flatten_ingredients

    out = flatten_ingredients("vegetable oil (sunflower, canola), salt, 2%")
    assert "sunflower oil" in out
    assert "canola oil" in out
    assert "salt" in out
    assert "2%" not in out


def test_user_profile_is_empty():
    """Empty profile (No rules, no allergens/lifestyle) is_empty()."""
    from core.models.user_profile import UserProfile
    p = UserProfile(user_id="u1", dietary_preference="No rules", allergens=[], lifestyle=[])
    assert p.is_empty() is True
    p2 = UserProfile(user_id="u2", dietary_preference="Jain", allergens=[], lifestyle=[])
    assert p2.is_empty() is False


def test_user_profile_update_merge():
    """Update_merge only changes provided fields; does not set others to None."""
    from core.models.user_profile import UserProfile
    p = UserProfile(user_id="u1", dietary_preference="Vegan", allergens=["Milk"], lifestyle=[])
    p.update_merge(allergens=["Egg"])
    assert p.dietary_preference == "Vegan"
    assert p.allergens == ["Egg"]


def test_user_profile_from_dict():
    """from_dict accepts user_id, dietary_preference, allergens, lifestyle."""
    from core.models.user_profile import UserProfile
    p = UserProfile.from_dict({
        "user_id": "u1",
        "dietary_preference": "Vegan",
        "allergens": ["Milk"],
        "lifestyle": ["no alcohol"],
    })
    assert p.user_id == "u1"
    assert p.dietary_preference == "Vegan"
    assert "Milk" in p.allergens
    assert "no alcohol" in [x.lower() for x in p.lifestyle]


def test_profile_storage_merge():
    """update_profile_partial only updates provided fields; does not reset to None."""
    from unittest.mock import patch
    from core.profile_storage import update_profile_partial
    from core.models.user_profile import UserProfile
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profiles.json"
        path.write_text(json.dumps({
            "p1": {"dietary_preference": "Jain", "allergens": ["Nuts"], "lifestyle": []}
        }, indent=2))
        with patch("core.profile_storage._PROFILES_PATH", path):
            out = update_profile_partial("p1", lifestyle=["no alcohol"])
        assert out is not None
        assert out.dietary_preference == "Jain"
        assert "Nuts" in out.allergens
        assert "no alcohol" in (out.lifestyle or [])


def test_verdict_informational_ingredients():
    """ComplianceVerdict includes informational_ingredients (minor <2%)."""
    from core.models.verdict import ComplianceVerdict, VerdictStatus
    v = ComplianceVerdict(
        status=VerdictStatus.SAFE,
        triggered_restrictions=[],
        triggered_ingredients=[],
        uncertain_ingredients=[],
        informational_ingredients=["salt", "yeast"],
        confidence_score=1.0,
    )
    assert v.informational_ingredients == ["salt", "yeast"]
    d = v.to_dict()
    assert "informational_ingredients" in d
    assert d["informational_ingredients"] == ["salt", "yeast"]


def test_profile_not_saved_on_ingredient_submission():
    """Chat with ingredients only must not call save_profile (profile persists; only /update or dialog save)."""
    from unittest.mock import patch
    from core.profile_storage import get_or_create_profile
    from core.intent_detector import detect_intent
    import app as app_module
    save_calls = []

    def track_save(profile):
        save_calls.append(profile)

    with patch("core.profile_storage.save_profile", side_effect=track_save):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            path.write_text(json.dumps({
                "test_u": {"user_id": "test_u", "dietary_preference": "Vegan", "allergens": [], "lifestyle": []}
            }, indent=2))
            with patch("core.profile_storage._PROFILES_PATH", path):
                profile = get_or_create_profile("test_u")
                field_name, values = app_module._parse_update_command("water, sugar")
                assert field_name is None and values is None
                parsed = detect_intent("water, sugar")
                ingredients = parsed.ingredients
                assert len(ingredients) >= 2
                from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
                restriction_ids = user_profile_model_to_restriction_ids(profile)
                profile_context = {
                    "dietary_preference": profile.dietary_preference,
                    "allergens": profile.allergens,
                    "lifestyle": profile.lifestyle,
                }
                run_new_engine_chat(
                    ingredients,
                    user_profile=profile,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                    use_api_fallback=False,
                )
        assert len(save_calls) == 0, "save_profile must not be called when submitting ingredients only (no /update)"
