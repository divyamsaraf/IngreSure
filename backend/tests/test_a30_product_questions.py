"""A30: product-shaped questions ask for the label and never firm-SAFE."""
import os

os.environ.setdefault("RATE_LIMIT_CHAT_ANON", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_AUTH", "100000/minute")
os.environ.setdefault("LLM_ENABLED", "false")

from fastapi.testclient import TestClient

from app import app
from core.parsing.ingredient_block import extract_ingredient_block
from core.stream_tags import INGREDIENT_AUDIT_TAG

client = TestClient(app, raise_server_exceptions=False)

_PRODUCT_QUESTIONS = [
    "Is Nutella vegan?",
    "Is Maggi masala gluten free?",
    "Is Oreo vegan?",
    "Is Kit Kat gluten free?",
    "Are Doritos vegan?",
    "Is Parle-G gluten free?",
    "Is Amul butter vegan?",
    "Is Cadbury Dairy Milk dairy free?",
    "Are Pringles vegan?",
    "Is Coca-Cola vegan?",
    "Is Pepsi gluten free?",
    "Are Lay's vegan?",
    "Is Maggi vegan?",
    "Is KitKat dairy free?",
    "Is Twix vegan?",
    "Is Snickers peanut free?",
    "Is Digestive biscuit gluten free?",
    "Is Vegemite vegan?",
    "Is Marmite gluten free?",
    "Is Weetabix vegan?",
    "Is Corn Flakes gluten free?",
    "Is McVitie's vegan?",
    "Is Tim Tam dairy free?",
    "Is Bournvita vegan?",
    "Is Horlicks gluten free?",
    "Is Parle Monaco vegan?",
    "Is Good Day biscuits gluten free?",
    "Is Dairy Milk vegan?",
    "Is Ferrero Rocher vegan?",
    "Is Pringles sour cream gluten free?",
]


def test_diet_question_about_unknown_brand_is_product_name():
    block = extract_ingredient_block("Is Nutella vegan?")
    assert block.kind == "product_name"
    block = extract_ingredient_block("Is Maggi masala gluten free?")
    assert block.kind == "product_name"


def test_known_ingredient_diet_question_is_not_product_name():
    block = extract_ingredient_block("is gelatin vegan?")
    assert block.kind != "product_name"


def test_cadbury_dairy_milk_not_safe_from_milk_token_alone():
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "Cadbury Dairy Milk", "restriction_ids": ["gluten_free"]},
    )
    assert r.status_code == 200
    assert r.json()["verdict"]["status"] != "SAFE"


def test_thirty_product_questions_ask_or_uncertain_never_safe():
    assert len(_PRODUCT_QUESTIONS) == 30
    for i, query in enumerate(_PRODUCT_QUESTIONS):
        r = client.post(
            "/chat/grocery",
            json={
                "query": query,
                "user_id": f"a30-gold-{i}",
                "userProfile": {
                    "dietary_preference": "Vegan",
                    "allergens": [],
                    "lifestyle": [],
                },
            },
        )
        assert r.status_code == 200, query
        text = r.text
        low = text.lower()
        asked = "ingredient list" in low or "product name" in low
        audit = None
        start = text.find(INGREDIENT_AUDIT_TAG)
        if start != -1:
            end = text.find(INGREDIENT_AUDIT_TAG, start + len(INGREDIENT_AUDIT_TAG))
            if end != -1:
                import json

                audit = json.loads(text[start + len(INGREDIENT_AUDIT_TAG) : end])
        if audit:
            statuses = {str(g.get("status") or "").lower() for g in (audit.get("groups") or [])}
            assert "safe" not in statuses, (query, statuses)
            assert asked or statuses <= {"depends", "uncertain", "check", "avoid", "not_safe"}
        else:
            assert asked, query
