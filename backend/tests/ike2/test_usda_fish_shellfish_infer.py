"""USDA FDC category/name → fish_source / shellfish_source (Item 37 / 42)."""
import importlib.util
from pathlib import Path

from core.external_apis.usda_fdc import (
    _fish_shellfish_from_name_and_category,
    _infer_flags_from_text,
)


def _transform_mod():
    path = Path(__file__).resolve().parents[2] / "scripts" / "transform_usda_fdc_bulk.py"
    spec = importlib.util.spec_from_file_location("transform_usda_fdc_bulk", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_finfish_category_sets_fish():
    flags = _infer_flags_from_text(
        "Fish, cod, Atlantic, raw",
        category="Finfish and Shellfish Products",
    )
    assert flags["fish_source"] is True
    assert flags["shellfish_source"] is False
    assert flags["animal_origin"] is True


def test_crustacean_name_sets_shellfish():
    flags = _infer_flags_from_text(
        "Crustaceans, crab, dungeness, raw",
        category="Finfish and Shellfish Products",
    )
    assert flags["shellfish_source"] is True
    assert flags["fish_source"] is False


def test_seafood_umbrella_sets_both():
    kind = _fish_shellfish_from_name_and_category("canned seafood", "")
    assert kind == {"fish_source": True, "shellfish_source": True}


def test_oyster_mushroom_not_shellfish():
    kind = _fish_shellfish_from_name_and_category("oyster mushroom dried", "")
    assert kind["shellfish_source"] is False


def test_layer1_emits_food_category_and_splits_markers():
    mod = _transform_mod()
    row = mod._food_to_layer1_row(
        {
            "description": "Fish, cod, Atlantic, raw",
            "foodCategory": "Finfish and Shellfish Products",
        },
        strict=False,
    )
    assert row is not None
    assert row["food_category"] == "Finfish and Shellfish Products"
    assert row["fish_source"] is True
    assert "usda_fdc_category_derived" in row["uncertainty_flags"]
    assert "usda_fdc_name_inferred" in row["uncertainty_flags"]


def test_layer1_category_only_generic_keeps_safe_ceiling():
    """Category hit without a fish/shellfish name token → derived + inferred ceiling."""
    mod = _transform_mod()
    # surimi is in _FISH_NAME — use a name with no lexicon hit
    row = mod._food_to_layer1_row(
        {
            "description": "Marine protein block prepared",
            "foodCategory": "Finfish and Shellfish Products",
        },
        strict=False,
    )
    assert row is not None
    assert row.get("fish_source") is True
    assert "usda_fdc_category_derived" in row["uncertainty_flags"]
    assert "usda_fdc_bulk_inferred" in row["uncertainty_flags"]
    assert row["food_category"] == "Finfish and Shellfish Products"
