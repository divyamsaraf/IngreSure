"""Product-shaped detector goldens: recall floor and brand+ingredient never-SAFE."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("RATE_LIMIT_CHAT_ANON", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_AUTH", "100000/minute")
os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")
os.environ.setdefault("LLM_ENABLED", "false")

from fastapi.testclient import TestClient

from app import app
from core.models.verdict import worst_external_status
from core.parsing.ingredient_block import extract_ingredient_block
from core.stream_tags import INGREDIENT_AUDIT_TAG

client = TestClient(app, raise_server_exceptions=False)

CORPUS = Path(__file__).parent / "corpus" / "product_shaped_goldens.jsonl"
MIN_PRODUCT_RECALL = 0.99
REQUIRED_MARKETS = {"IN", "US", "UK", "AU", "NZ", "CA", "EU", "UAE"}
REQUIRED_LANGS = {"en", "hi-en", "fr", "de"}
LABELS = {"product", "dish", "ingredient", "ambiguous"}
EXPECT_KINDS = {"product_name", "not_product_name"}
RESTRICTIONS = ("gluten_free", "vegan", "dairy_free", "peanut_allergy")

BRAND_WITH_INGREDIENT_WORD = (
    "Dairy Milk",
    "Almond Joy",
    "Honey Nut Cheerios",
    "Butterfinger",
    "Cream of Wheat",
    "Rice Krispies",
    "Milky Way",
    "Cadbury Dairy Milk",
    "Amul butter",
    "Maggi masala",
    "Maggi noodles",
    "Amul cheese",
    "Hershey's Milk Chocolate",
    "Philadelphia cream cheese",
    "Almond Breeze",
    "Honey Smacks",
    "Nestle Milkmaid",
    "Corn Flakes",
)

_CHAT_PROFILES = {
    "vegan": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
    "gluten_free": {
        "dietary_preference": "No rules",
        "allergens": [],
        "lifestyle": ["Gluten-Free"],
    },
    "dairy_free": {
        "dietary_preference": "No rules",
        "allergens": ["Milk"],
        "lifestyle": ["Dairy-Free"],
    },
    "peanut_allergy": {
        "dietary_preference": "No rules",
        "allergens": ["Peanut"],
        "lifestyle": [],
    },
}


def load_goldens() -> list[dict]:
    rows = []
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _predicted_product(query: str) -> bool:
    return extract_ingredient_block(query).kind == "product_name"


def _metrics(rows: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    misses = []
    false_positives = []
    for row in rows:
        predicted = _predicted_product(row["query"])
        actual = row["expect_kind"] == "product_name"
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
            false_positives.append(row["id"])
        elif not predicted and actual:
            fn += 1
            misses.append({"id": row["id"], "query": row["query"], "kind": extract_ingredient_block(row["query"]).kind})
        else:
            tn += 1
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "recall": recall,
        "precision": precision,
        "misses": misses,
        "false_positives": false_positives,
    }


def _parse_audit(text: str) -> dict | None:
    start = text.find(INGREDIENT_AUDIT_TAG)
    if start == -1:
        return None
    end = text.find(INGREDIENT_AUDIT_TAG, start + len(INGREDIENT_AUDIT_TAG))
    if end == -1:
        return None
    return json.loads(text[start + len(INGREDIENT_AUDIT_TAG) : end])


def _chat_not_safe(query: str, restriction_id: str, user_id: str) -> None:
    profile = _CHAT_PROFILES[restriction_id]
    r = client.post(
        "/chat/grocery",
        json={"query": query, "user_id": user_id, "userProfile": profile},
    )
    assert r.status_code == 200, (query, restriction_id, r.status_code, r.text[:300])
    text = r.text
    low = text.lower()
    asked = "ingredient list" in low or "product name" in low
    audit = _parse_audit(text)
    if audit:
        statuses = {str(g.get("status") or "").lower() for g in (audit.get("groups") or [])}
        # Mixed cards are allowed (wheat AVOID + cream SAFE). Overall is the gate.
        # OLD (too strict): assert "safe" not in statuses
        # BROKEN (PR #26): if "avoid" in statuses or "not_safe" in statuses: return
        #   that return skipped any overall assertion.
        overall = worst_external_status(statuses)
        assert overall != "SAFE", (query, restriction_id, overall, statuses)
        assert asked or statuses <= {"depends", "uncertain", "check", "avoid", "not_safe", "safe"}
    else:
        assert asked, (query, restriction_id, text[:400])


def test_corpus_has_200_labeled_rows():
    rows = load_goldens()
    assert len(rows) == 200
    ids = [r["id"] for r in rows]
    queries = [r["query"] for r in rows]
    assert len(set(ids)) == 200
    assert len(set(queries)) == 200
    for row in rows:
        assert set(row) >= {"id", "query", "label", "market", "lang", "expect_kind"}
        assert row["label"] in LABELS
        assert row["expect_kind"] in EXPECT_KINDS
        if row["label"] == "product":
            assert row["expect_kind"] == "product_name"
        else:
            assert row["expect_kind"] == "not_product_name"
    products = [r for r in rows if r["label"] == "product"]
    others = [r for r in rows if r["label"] != "product"]
    assert len(products) == 100
    assert len(others) == 100
    assert {r["label"] for r in others} <= {"dish", "ingredient", "ambiguous"}
    assert REQUIRED_MARKETS <= {r["market"] for r in products}
    langs = {r["lang"] for r in products}
    assert REQUIRED_LANGS <= langs
    corpus_queries = {r["query"] for r in rows}
    for name in BRAND_WITH_INGREDIENT_WORD:
        assert name in corpus_queries, name


def test_product_recall_at_least_99_percent():
    rows = load_goldens()
    m = _metrics(rows)
    print(
        f"product-shaped goldens precision={m['precision']:.4f} "
        f"recall={m['recall']:.4f} tp={m['tp']} fp={m['fp']} fn={m['fn']} tn={m['tn']}"
    )
    print("misses:", m["misses"] or "none")
    if m["false_positives"]:
        print("over-ask ids (ok):", m["false_positives"][:20], "..." if len(m["false_positives"]) > 20 else "")
    assert m["recall"] >= MIN_PRODUCT_RECALL, (
        f"product recall {m['recall']:.3f} < {MIN_PRODUCT_RECALL:.2f}; "
        f"precision={m['precision']:.3f}; misses={m['misses']}"
    )


@pytest.mark.parametrize("name", BRAND_WITH_INGREDIENT_WORD)
def test_brand_with_ingredient_word_is_product_name(name: str):
    block = extract_ingredient_block(name)
    assert block.kind == "product_name", (name, block.kind)


def test_cream_of_wheat_gluten_free_overall_is_not_safe():
    """Does not call _chat_not_safe, so no helper return can skip this.

    Cards may mix SAFE+AVOID; overall gluten_free status must be NOT_SAFE.
    """
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "Cream of Wheat", "restriction_ids": ["gluten_free"]},
    )
    assert r.status_code == 200, r.text[:300]
    assert r.json()["verdict"]["status"] == "NOT_SAFE", r.json()

    chat = client.post(
        "/chat/grocery",
        json={
            "query": "Cream of Wheat",
            "user_id": "ps-cream-of-wheat-overall",
            "userProfile": _CHAT_PROFILES["gluten_free"],
        },
    )
    assert chat.status_code == 200, chat.text[:300]
    audit = _parse_audit(chat.text)
    assert audit is not None, chat.text[:400]
    overall = worst_external_status(
        str(g.get("status") or "") for g in (audit.get("groups") or [])
    )
    assert overall == "NOT_SAFE", (overall, audit.get("groups"))


@pytest.mark.parametrize("name", BRAND_WITH_INGREDIENT_WORD)
@pytest.mark.parametrize("restriction_id", RESTRICTIONS)
def test_brand_with_ingredient_word_evaluate_product_not_safe(name: str, restriction_id: str):
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": name, "restriction_ids": [restriction_id]},
    )
    assert r.status_code == 200, (name, restriction_id, r.text[:300])
    assert r.json()["verdict"]["status"] != "SAFE", (name, restriction_id, r.json())


@pytest.mark.parametrize("name", BRAND_WITH_INGREDIENT_WORD)
@pytest.mark.parametrize("restriction_id", RESTRICTIONS)
def test_brand_with_ingredient_word_chat_not_safe(name: str, restriction_id: str):
    slug = name.lower().replace(" ", "-").replace("'", "")
    _chat_not_safe(name, restriction_id, user_id=f"ps-brand-{slug}-{restriction_id}")
