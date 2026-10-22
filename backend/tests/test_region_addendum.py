"""R01–R06: region profile is display/defaults only; detection is the union."""
from fastapi.testclient import TestClient

from app import app
from core.emergency import generic_guidance, number_for_region
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings
from core.region_profile import allergen_detection_ids

client = TestClient(app, raise_server_exceptions=False)


def test_r01_unknown_region_lists_common_numbers():
    text = generic_guidance()
    for n in ("911", "999", "112", "000", "111", "998"):
        assert n in text
    assert allergen_detection_ids(None) == allergen_detection_ids("CA") == allergen_detection_ids("US")
    assert number_for_region(None) is None


def test_canada_911_once_verified():
    assert number_for_region("CA") == "911"


def test_r02_uk_names_map():
    atoms = preprocess_ingredients_to_strings(
        "aubergine, courgette, coriander, prawns, plain flour, caster sugar"
    )
    blob = " ".join(atoms).lower()
    assert "aubergine" in blob or "eggplant" in blob
    assert "courgette" in blob or "zucchini" in blob
    assert "coriander" in blob or "cilantro" in blob
    assert "prawn" in blob or "shrimp" in blob
    assert "flour" in blob
    assert "sugar" in blob


def test_r03_fdc_colors_keep_identity():
    atoms = preprocess_ingredients_to_strings("FD&C Red No. 40, Yellow 5 Lake, Blue 1")
    blob = " ".join(atoms).lower().replace(" ", "")
    assert "40" in blob or "red" in blob or "e129" in blob
    assert "5" in blob or "yellow" in blob or "e102" in blob
    assert "blue" in blob or "1" in blob or "e133" in blob


def test_r04_french_contains_is_kept():
    atoms = preprocess_ingredients_to_strings(
        "Contains: wheat, milk, mustard / gluten source: oats / Contient: ble, lait"
    )
    blob = " ".join(atoms).lower()
    assert "wheat" in blob or "blé" in blob or "ble" in blob
    assert "milk" in blob or "lait" in blob
    assert "mustard" in blob or "moutarde" in blob
    assert "oat" in blob


def test_r05_oats_not_cleared_by_gluten_free_claim():
    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "gluten free oats, salt",
            "restriction_ids": ["gluten_free"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] != "SAFE"


def test_r06_halal_meat_without_cert_is_not_safe():
    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "chicken, beef",
            "restriction_ids": ["halal"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] != "SAFE"
