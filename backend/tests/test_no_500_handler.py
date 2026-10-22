"""Item 52a: evaluate/chat never HTTP 500; parser/engine exceptions fail closed."""
from __future__ import annotations

import random

from fastapi.testclient import TestClient

from app import app
from core.models.verdict import VerdictStatus

client = TestClient(app, raise_server_exceptions=False)

_FUZZ = [
    "PEANUTS (49.5%), honey, salt",
    "wheat flour (min. 62%), water",
    "Reismehl, löslicher Ballaststoff: Oligofructose , Hydroxyprpylmethylcellulose (Kapselhülle)",
    "Omega-3-Algenöl, MCT-ÖI&quot;, Bor retschöl&quot; (long paren nested (a (b (c))))",
    "Water, diluent (xylitol), cholecalciferol (vitamin D3), emulsifiers (acacia gum and sunflower lecithin)",
    "a (" * 40 + "x" + ")" * 40,
    "pеanuts",  # homoglyph
    "water\x00peanut",
    "<script>alert(1)</script>, peanuts",
    "less than 2% of: salt, natural flavor",
    "E322, E471, sugar (99%)",
    "and/or sunflower oil (palm (kernel (olein)))",
]


def test_evaluate_product_parser_exception_is_uncertain_200(monkeypatch):
    from core.api.v1 import routes as routes_mod

    def boom(_text):
        raise RuntimeError("dictionary changed size during iteration")

    monkeypatch.setattr(routes_mod, "preprocess_ingredients_to_strings", boom)
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "water, salt", "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200, r.text[:400]
    body = r.json()
    assert body["verdict"]["status"] == VerdictStatus.UNCERTAIN.value
    assert "parsed_ingredients" in body


def test_evaluate_compliance_engine_exception_is_uncertain_200(monkeypatch):
    import core.bridge as bridge

    def boom(*_a, **_k):
        raise RuntimeError("dictionary changed size during iteration")

    monkeypatch.setattr(bridge, "_run_ike2_compliance", boom)
    r = client.post(
        "/api/v1/evaluate-compliance",
        json={"ingredients": ["water"], "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200, r.text[:400]
    assert r.json()["verdict"]["status"] == VerdictStatus.UNCERTAIN.value


def test_chat_engine_exception_is_not_500(monkeypatch):
    import app as app_mod

    def boom(*_a, **_k):
        raise RuntimeError("dictionary changed size during iteration")

    monkeypatch.setattr(app_mod, "run_new_engine_chat", boom)
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Ingredients: milk, water",
            "user_id": "no500-chat",
            "userProfile": {
                "dietary_preference": "Vegan",
                "allergens": [],
                "lifestyle": [],
            },
        },
    )
    assert r.status_code == 200, r.text[:400]
    assert "UNCERTAIN" in r.text.upper() or "could not" in r.text.lower()


_FUZZ_PLUS_RANDOM = _FUZZ + [
    "".join(chr(random.Random(i).randint(32, 126)) for _ in range(80)) for i in range(8)
]


def test_evaluate_product_fuzz_never_500():
    for text in _FUZZ_PLUS_RANDOM:
        r = client.post(
            "/api/v1/evaluate-product",
            json={"ingredients_text": text, "restriction_ids": ["vegan"]},
        )
        assert r.status_code != 500, f"{text[:80]!r} -> {r.status_code} {r.text[:200]}"
        if r.status_code == 200:
            assert r.json()["verdict"]["status"] in {"SAFE", "NOT_SAFE", "UNCERTAIN"}
