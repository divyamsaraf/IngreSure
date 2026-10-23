"""Parser must not hang on pathological labels (512KB body cap)."""
import os
import time

os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_ANON", "100000/minute")

from fastapi.testclient import TestClient

from app import app
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings

client = TestClient(app, raise_server_exceptions=False)
_KB512 = 512 * 1024


def _assert_parse_under(text: str, budget_s: float = 2.0) -> list[str]:
    t0 = time.perf_counter()
    out = preprocess_ingredients_to_strings(text)
    dt = time.perf_counter() - t0
    assert dt < budget_s, f"parse took {dt:.3f}s on {len(text)} bytes"
    return out


def test_512kb_repeated_and_under_2s():
    raw = (" and water" * (_KB512 // 10))[:_KB512]
    out = _assert_parse_under(raw)
    assert any("water" in a.lower() for a in out)


def test_512kb_long_run_of_one_char_under_2s():
    _assert_parse_under("a" * _KB512)


def test_nested_parens_under_2s():
    depth = 200
    raw = "(" * depth + "water, salt" + ")" * depth
    out = _assert_parse_under(raw)
    assert any("water" in a.lower() for a in out)


def test_near_miss_and_inside_parens_under_2s():
    inner = " and water" * 4000
    raw = "chocolate (" + inner.strip() + "), flour"
    out = _assert_parse_under(raw)
    assert any("flour" in a.lower() for a in out)


def test_parse_budget_exceeded_is_degraded_uncertain(monkeypatch):
    import core.parsing.ingredient_parser as parser

    monkeypatch.setattr(parser, "PARSE_BUDGET_S", 0.0)
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "water, salt", "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] == "UNCERTAIN"
    assert body["verdict"]["degraded"] is True
