"""Phase 5 — OCR noise and multi-block label selection."""

from core.normalization.normalizer import normalize_ingredient_key
from core.parsing.label_decomposer import decompose_label
from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text


class TestOcrLabelNoise:
    def test_fix_ingred1ents_prefix(self):
        raw = "Ingred1ents: water, salt"
        assert "Ingredients:" in fix_ocr_label_noise(raw)

    def test_fix_broken_comma_l_dot(self):
        raw = "water l. salt l. sugar"
        fixed = fix_ocr_label_noise(raw)
        assert fixed == "water, salt, sugar"

    def test_normalize_ocr_token_typos(self):
        assert normalize_ingredient_key("mi1k") == "milk"
        assert normalize_ingredient_key("fl0ur") == "flour"
        assert normalize_ingredient_key("s0y") == "soy"
        assert normalize_ingredient_key("whe4t") == "wheat"

    def test_decompose_ocr_label(self):
        items = decompose_label("Ingred1ents: mi1k, fl0ur, s0y")
        names = {i.name for i in items}
        assert "milk" in names
        assert "flour" in names
        assert "soy" in names


class TestMultiBlockLabel:
    def test_prefers_last_ingredients_block(self):
        raw = (
            "Ingredients: water\n\n"
            "Ingredients: milk, sugar, salt, yeast"
        )
        selected = select_ingredient_label_text(raw)
        assert "milk" in selected
        assert selected.lower().startswith("ingredients")

    def test_largest_comma_segment_without_header(self):
        raw = (
            "Nutrition Facts Calories 200\n"
            "water\n"
            "milk, sugar, flour, salt, yeast"
        )
        selected = select_ingredient_label_text(raw)
        assert "milk" in selected
        assert selected.count(",") >= 3

    def test_strips_active_ingredient_suffix(self):
        raw = (
            "Ingredients: water, flour. "
            "Active Ingredient Name Vegetable Juice (Water, Carrots)."
        )
        selected = select_ingredient_label_text(raw)
        assert "active ingredient name" not in selected.lower()
        assert "water" in selected


class TestRegionalNormalizer:
    def test_bajra_maps_to_pearl_millet(self):
        assert normalize_ingredient_key("bajra") == "pearl millet"

    def test_atta_maps_to_wheat_flour(self):
        assert normalize_ingredient_key("atta") == "wheat flour"

    def test_haldi_maps_to_turmeric(self):
        assert normalize_ingredient_key("haldi") == "turmeric"
