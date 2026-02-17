"""
Comprehensive restriction verification test suite.
Covers all dietary, religious, lifestyle, and allergy restrictions
with explicit expected outcomes for common ingredients.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pytest
from core.evaluation.compliance_engine import ComplianceEngine
from core.models.verdict import VerdictStatus


@pytest.fixture(scope="module")
def engine():
    return ComplianceEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _eval(engine, ingredient, restriction):
    v = engine.evaluate([ingredient], restriction_ids=[restriction], use_api_fallback=False)
    return v.status


# ---------------------------------------------------------------------------
# HALAL: prohibits pork, alcohol, insect-derived; allows meat, fish, dairy, eggs
# ---------------------------------------------------------------------------
class TestHalal:
    @pytest.mark.parametrize("ingredient", [
        "pork", "bacon", "lard", "ham",
    ])
    def test_pork_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "halal") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "wine", "beer", "rum", "vodka",
    ])
    def test_alcohol_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "halal") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "shellac", "carmine",
    ])
    def test_insect_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "halal") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "gelatin",
    ])
    def test_halal_gelatin_not_safe(self, engine, ingredient):
        """Gelatin is pig-derived (E441); not halal."""
        assert _eval(engine, ingredient, "halal") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "lamb", "fish", "tuna", "salmon",
        "milk", "egg", "butter", "cheese",
        "sugar", "rice", "wheat", "tofu",
    ])
    def test_halal_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "halal") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# KOSHER: prohibits pork, shellfish, insect-derived; allows meat, fish, dairy, eggs
# ---------------------------------------------------------------------------
class TestKosher:
    @pytest.mark.parametrize("ingredient", [
        "pork", "bacon", "lard", "ham",
    ])
    def test_pork_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "kosher") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "shrimp", "crab", "lobster", "prawn",
    ])
    def test_shellfish_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "kosher") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "shellac", "carmine",
    ])
    def test_insect_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "kosher") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "gelatin",
    ])
    def test_kosher_gelatin_not_safe(self, engine, ingredient):
        """Gelatin is pig-derived (E441); not kosher."""
        assert _eval(engine, ingredient, "kosher") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "lamb", "fish", "salmon", "tuna",
        "milk", "egg", "sugar",
    ])
    def test_kosher_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "kosher") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# HINDU VEGETARIAN: prohibits meat, fish, egg, insect-derived; allows dairy
# ---------------------------------------------------------------------------
class TestHinduVegetarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "fish", "tuna", "salmon",
        "egg", "gelatin", "collagen", "castoreum",
        "isinglass", "anchovy", "shellac", "honey",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "hindu_vegetarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "milk", "butter", "ghee", "cheese",
        "water", "sugar", "rice", "wheat",
        "onion", "garlic", "tofu", "mushroom",
        "coconut", "peanut butter", "almond milk",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "hindu_vegetarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# HINDU NON-VEGETARIAN: prohibits beef/cow, insect-derived; allows other meat, fish, dairy, eggs
# ---------------------------------------------------------------------------
class TestHinduNonVegetarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "shellac", "carmine", "beeswax",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "hindu_non_vegetarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "chicken", "fish", "lamb", "tuna",
        "milk", "egg", "butter", "cheese",
        "rice", "sugar", "tofu",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "hindu_non_vegetarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# JAIN: prohibits meat, fish, egg, insect, root veg, alcohol, onion, garlic; allows dairy
# ---------------------------------------------------------------------------
class TestJain:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "fish", "egg", "gelatin",
        "onion", "garlic", "potato", "carrot",
        "wine", "beer", "honey", "shellac",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "jain") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "milk", "sugar", "rice", "wheat",
        "tofu", "tomato", "spinach", "coconut",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "jain") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# VEGAN: prohibits all animal products (dairy, eggs, honey, meat, fish, insect)
# ---------------------------------------------------------------------------
class TestVegan:
    @pytest.mark.parametrize("ingredient", [
        "milk", "egg", "honey", "gelatin",
        "beef", "fish", "beeswax", "shellac",
        "lanolin", "collagen", "butter", "cheese",
        "whey", "casein", "cream", "ghee",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "vegan") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "water", "sugar", "rice", "tofu", "tempeh",
        "seitan", "coconut", "almond milk", "oat milk",
        "soy milk", "peanut butter", "mushroom", "agar",
        "vinegar", "cinnamon", "black pepper",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "vegan") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# VEGETARIAN: prohibits meat/fish; allows dairy, eggs, honey
# ---------------------------------------------------------------------------
class TestVegetarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "fish", "gelatin", "collagen",
        "lard", "tallow",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "vegetarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "milk", "egg", "cheese", "honey", "tofu",
        "rice", "sugar", "butter", "mushroom",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "vegetarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# LACTO VEGETARIAN: prohibits meat/fish/eggs; allows dairy, honey
# ---------------------------------------------------------------------------
class TestLactoVegetarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "fish", "egg", "gelatin",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "lacto_vegetarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "milk", "cheese", "butter", "honey", "rice", "sugar",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "lacto_vegetarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# OVO VEGETARIAN: prohibits meat/fish/dairy; allows eggs, honey
# ---------------------------------------------------------------------------
class TestOvoVegetarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "fish", "milk", "cheese", "butter",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "ovo_vegetarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "egg", "honey", "rice", "sugar", "tofu",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "ovo_vegetarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# PESCATARIAN: prohibits land meat; allows fish, dairy, eggs
# ---------------------------------------------------------------------------
class TestPescatarian:
    @pytest.mark.parametrize("ingredient", [
        "beef", "chicken", "pork", "lamb",
    ])
    def test_not_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "pescatarian") == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient", [
        "fish", "tuna", "shrimp", "salmon",
        "milk", "egg", "honey", "rice",
    ])
    def test_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "pescatarian") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# MEDICAL / ALLERGY
# ---------------------------------------------------------------------------
class TestMedicalAllergy:
    @pytest.mark.parametrize("ingredient,restriction", [
        ("wheat", "gluten_free"), ("barley", "gluten_free"),
        ("milk", "dairy_free"), ("butter", "dairy_free"),
        ("egg", "egg_free"),
        ("peanut", "peanut_allergy"),
        ("almond", "tree_nut_allergy"),
        ("shrimp", "shellfish_allergy"), ("crab", "shellfish_allergy"),
        ("tuna", "fish_allergy"), ("salmon", "fish_allergy"),
        ("sesame", "sesame_allergy"),
        ("onion", "onion_allergy"),
        ("garlic", "garlic_allergy"),
    ])
    def test_allergy_not_safe(self, engine, ingredient, restriction):
        assert _eval(engine, ingredient, restriction) == VerdictStatus.NOT_SAFE

    @pytest.mark.parametrize("ingredient,restriction", [
        ("rice", "gluten_free"),
        ("chicken", "dairy_free"),
        ("rice", "peanut_allergy"),
        ("rice", "sesame_allergy"),
    ])
    def test_allergy_safe(self, engine, ingredient, restriction):
        assert _eval(engine, ingredient, restriction) == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# BUDDHIST / SEVENTH DAY ADVENTIST
# ---------------------------------------------------------------------------
class TestBuddhistSDA:
    def test_buddhist_pork_not_safe(self, engine):
        assert _eval(engine, "pork", "buddhist_default") == VerdictStatus.NOT_SAFE

    def test_buddhist_rice_safe(self, engine):
        assert _eval(engine, "rice", "buddhist_default") == VerdictStatus.SAFE

    def test_sda_alcohol_not_safe(self, engine):
        assert _eval(engine, "wine", "seventh_day_adventist_default") == VerdictStatus.NOT_SAFE

    def test_sda_rice_safe(self, engine):
        assert _eval(engine, "rice", "seventh_day_adventist_default") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# LIFESTYLE: no_onion, no_garlic, no_alcohol
# ---------------------------------------------------------------------------
class TestLifestyle:
    def test_no_onion(self, engine):
        assert _eval(engine, "onion", "no_onion") == VerdictStatus.NOT_SAFE

    def test_no_garlic(self, engine):
        assert _eval(engine, "garlic", "no_garlic") == VerdictStatus.NOT_SAFE

    def test_no_alcohol_wine(self, engine):
        assert _eval(engine, "wine", "no_alcohol") == VerdictStatus.NOT_SAFE

    def test_no_alcohol_rice_safe(self, engine):
        assert _eval(engine, "rice", "no_alcohol") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# EDGE CASES: plant-based items should NOT be flagged as animal
# ---------------------------------------------------------------------------
class TestPlantBasedEdgeCases:
    @pytest.mark.parametrize("ingredient", [
        "tofu", "tempeh", "seitan", "soybean",
        "peanut butter", "almond milk", "oat milk", "soy milk",
        "coconut milk", "coconut", "mushroom", "agar",
    ])
    def test_vegan_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "vegan") == VerdictStatus.SAFE

    @pytest.mark.parametrize("ingredient", [
        "tofu", "soybean", "peanut butter",
    ])
    def test_jain_safe(self, engine, ingredient):
        assert _eval(engine, ingredient, "jain") == VerdictStatus.SAFE


# ---------------------------------------------------------------------------
# USDA FETCHER: _infer_flags_from_text with category
# ---------------------------------------------------------------------------
class TestUSDAFlagInference:
    """Verify that the fixed USDA flag inference correctly classifies items."""

    def test_peanut_butter_not_dairy(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Peanut butter, smooth", category="Legumes and Legume Products")
        assert flags["animal_origin"] is False
        assert flags["dairy_source"] is False
        assert flags["plant_origin"] is True

    def test_almond_milk_not_dairy(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Almond milk, unsweetened", category="Beverages")
        assert flags["animal_origin"] is False
        assert flags["dairy_source"] is False
        assert flags["plant_origin"] is True

    def test_tofu_not_animal(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Tofu, firm, prepared with calcium sulfate", category="Legumes and Legume Products")
        assert flags["animal_origin"] is False
        assert flags["plant_origin"] is True
        assert flags["soy_source"] is True

    def test_banana_not_animal(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Bananas, raw", category="Fruits and Fruit Juices")
        assert flags["animal_origin"] is False
        assert flags["plant_origin"] is True
        assert flags["dairy_source"] is False

    def test_beef_is_animal(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Beef, ground, 80% lean meat / 20% fat", category="Beef Products")
        assert flags["animal_origin"] is True
        assert flags["plant_origin"] is False

    def test_cheese_is_dairy(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Cheese, cheddar", category="Dairy and Egg Products")
        assert flags["dairy_source"] is True
        assert flags["animal_origin"] is True

    def test_eggplant_not_egg(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Eggplant, raw", category="Vegetables and Vegetable Products")
        assert flags["egg_source"] is False
        assert flags["plant_origin"] is True

    def test_butternut_squash_not_dairy(self):
        from core.external_apis.usda_fdc import _infer_flags_from_text
        flags = _infer_flags_from_text("Butternut squash, raw", category="Vegetables and Vegetable Products")
        assert flags["dairy_source"] is False
        assert flags["plant_origin"] is True


# ---------------------------------------------------------------------------
# NORMALIZER: variant resolution
# ---------------------------------------------------------------------------
class TestNormalizerVariants:
    def test_eggs_to_egg(self):
        from core.normalization.normalizer import normalize_ingredient_key
        assert normalize_ingredient_key("eggs") == "egg"

    def test_anchovies_to_anchovy(self):
        from core.normalization.normalizer import normalize_ingredient_key
        assert normalize_ingredient_key("anchovies") == "anchovy"

    def test_gelatine_to_gelatin(self):
        from core.normalization.normalizer import normalize_ingredient_key
        assert normalize_ingredient_key("gelatine") == "gelatin"

    def test_e120_to_carmine(self):
        from core.normalization.normalizer import normalize_ingredient_key
        assert normalize_ingredient_key("E120") == "carmine"

    def test_inglass_to_isinglass(self):
        from core.normalization.normalizer import normalize_ingredient_key
        assert normalize_ingredient_key("inglass") == "isinglass"
