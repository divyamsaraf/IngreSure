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
    from core.normalization.normalizer import normalize_ingredient_key, KNOWN_VARIANTS
    assert normalize_ingredient_key("inglass") == "isinglass"
    assert normalize_ingredient_key("Isinglass") == "isinglass"
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


def test_user_profile_is_empty():
    """Empty profile (No rules, no allergens/lifestyle/religious) is_empty()."""
    from core.models.user_profile import UserProfile
    p = UserProfile(user_id="u1", dietary_preference="No rules", allergens=[], lifestyle=[], religious_preferences=[])
    assert p.is_empty() is True
    p2 = UserProfile(user_id="u2", dietary_preference="Jain", allergens=[], lifestyle=[], religious_preferences=[])
    assert p2.is_empty() is False


def test_user_profile_update_merge():
    """Update_merge only changes provided fields; does not set others to None."""
    from core.models.user_profile import UserProfile
    p = UserProfile(user_id="u1", dietary_preference="Vegan", allergens=["Milk"], lifestyle=[], religious_preferences=[])
    p.update_merge(allergens=["Egg"])
    assert p.dietary_preference == "Vegan"
    assert p.allergens == ["Egg"]


def test_user_profile_from_dict_legacy():
    """from_dict accepts legacy keys (dietary_restrictions, lifestyle_flags)."""
    from core.models.user_profile import UserProfile
    p = UserProfile.from_dict({
        "user_id": "u1",
        "dietary_restrictions": ["vegan"],
        "allergens": ["Milk"],
        "lifestyle_flags": ["no alcohol"],
        "religious_preferences": ["halal"],
    })
    assert p.dietary_preference in ("vegan", "Vegan") or "vegan" in p.dietary_preference.lower()
    assert "Milk" in p.allergens or "milk" in [a.lower() for a in p.allergens]
    assert p.lifestyle or "no alcohol" in [x.lower() for x in p.lifestyle]


def test_profile_storage_merge():
    """update_profile_partial only updates provided fields; does not reset to None."""
    from unittest.mock import patch
    from core.profile_storage import update_profile_partial
    from core.models.user_profile import UserProfile
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profiles.json"
        path.write_text(json.dumps({
            "p1": {"dietary_preference": "Jain", "allergens": ["Nuts"], "lifestyle": [], "religious_preferences": []}
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
    from safety_analyst import SafetyAnalyst
    import app as app_module
    save_calls = []

    def track_save(profile):
        save_calls.append(profile)

    with patch("core.profile_storage.save_profile", side_effect=track_save):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            path.write_text(json.dumps({
                "test_u": {"user_id": "test_u", "dietary_preference": "Vegan", "allergens": [], "lifestyle": [], "religious_preferences": []}
            }, indent=2))
            with patch("core.profile_storage._PROFILES_PATH", path):
                profile = get_or_create_profile("test_u")
                field_name, values = app_module._parse_update_command("water, sugar")
                assert field_name is None and values is None
                ingredients = SafetyAnalyst._extract_ingredients("water, sugar")
                assert len(ingredients) >= 2
                from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
                restriction_ids = user_profile_model_to_restriction_ids(profile)
                profile_context = {
                    "dietary_preference": profile.dietary_preference,
                    "allergens": profile.allergens,
                    "religious_preferences": profile.religious_preferences,
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
