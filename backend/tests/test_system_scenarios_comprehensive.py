"""
Broad scenario tests: substance dedup, E-numbers, diets, LLM on/off chat paths.
Compliance is always deterministic; LLM only affects explanation prose when enabled.
"""
import json
import os
import re
from typing import List, Optional, Set

import pytest
from fastapi.testclient import TestClient

from core.normalization.normalizer import KNOWN_VARIANTS, substance_key, is_e_number_code
from core.response_composer import build_ingredient_audit_payload, count_safe_audit_ingredients
from core.stream_tags import INGREDIENT_AUDIT_TAG


class _Profile:
    def __init__(self, dietary_preference="Vegan", allergens=None, lifestyle=None):
        self.dietary_preference = dietary_preference
        self.allergens = allergens or []
        self.lifestyle = lifestyle or []


def _group_names(payload, status):
    return [
        item["name"]
        for group in payload.get("groups", [])
        if group.get("status") == status
        for item in group.get("items", [])
    ]


def _substance_keys_from_payload(payload) -> dict:
    """Collect substance keys per audit group for overlap checks."""
    out = {}
    for group in payload.get("groups", []):
        status = group.get("status")
        keys = set()
        for item in group.get("items", []):
            name = item.get("name", "")
            keys.add(substance_key(name))
            if " · " in name:
                keys.add(substance_key(name.split(" · ", 1)[1]))
        out[status] = keys
    return out


def _assert_no_avoid_safe_overlap(payload):
    keys = _substance_keys_from_payload(payload)
    avoid = keys.get("avoid", set())
    safe = keys.get("safe", set())
    overlap = (avoid & safe) - {""}
    assert not overlap, f"Substance in both Avoid and Safe: {overlap}"


def _extract_audit(body: str):
    start = body.find(INGREDIENT_AUDIT_TAG)
    if start == -1:
        return None
    end = body.find(INGREDIENT_AUDIT_TAG, start + len(INGREDIENT_AUDIT_TAG))
    if end == -1:
        return None
    return json.loads(body[start + len(INGREDIENT_AUDIT_TAG) : end])


E_NUMBER_VARIANTS = sorted({k for k in KNOWN_VARIANTS if re.match(r"^e\d", k, re.I)})


@pytest.mark.parametrize("e_code", E_NUMBER_VARIANTS)
def test_e_number_variant_no_avoid_safe_duplicate(e_code):
    """Every KNOWN_VARIANTS E-number must not duplicate in Avoid+Safe when triggered."""
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids

    substance = KNOWN_VARIANTS[e_code]
    profile = _Profile(dietary_preference="Hindu Vegetarian")
    rids = user_profile_model_to_restriction_ids(profile)
    verdict = run_new_engine_chat(
        [e_code, substance],
        user_profile=profile,
        restriction_ids=rids,
        use_api_fallback=False,
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=profile,
        ingredients=[e_code, substance],
    )
    _assert_no_avoid_safe_overlap(payload)
    if verdict.triggered_ingredients:
        assert _group_names(payload, "safe") == [] or substance_key(e_code) not in {
            substance_key(n) for n in _group_names(payload, "safe")
        }


@pytest.mark.parametrize(
    "diet,trigger_ingredient",
    [
        ("Vegan", "milk"),
        ("Vegan", "egg"),
        ("Jain", "onion"),
        ("Jain", "yam"),
        ("Halal", "pork"),
        ("Kosher", "shellfish"),
        ("Hindu Vegetarian", "e120"),
        ("Vegetarian", "e441"),
    ],
)
def test_diet_trigger_no_safe_duplicate(diet, trigger_ingredient):
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids

    profile = _Profile(dietary_preference=diet)
    rids = user_profile_model_to_restriction_ids(profile)
    verdict = run_new_engine_chat(
        [trigger_ingredient, "sugar", "salt"],
        user_profile=profile,
        restriction_ids=rids,
        use_api_fallback=False,
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=profile,
        ingredients=[trigger_ingredient, "sugar", "salt"],
    )
    _assert_no_avoid_safe_overlap(payload)
    if verdict.triggered_ingredients:
        sk = substance_key(trigger_ingredient)
        safe_keys = {substance_key(n) for n in _group_names(payload, "safe")}
        assert sk not in safe_keys


def test_ontology_substance_keys_merge_consistently():
    """Registry must resolve E-number and alias to same substance entry."""
    from core.config import get_ontology_path
    from core.ontology.ingredient_registry import IngredientRegistry

    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    reg = IngredientRegistry()
    for e_code in E_NUMBER_VARIANTS:
        substance = KNOWN_VARIANTS[e_code]
        ing_e = reg.resolve(e_code)
        ing_s = reg.resolve(substance)
        if ing_e and ing_s:
            assert substance_key(ing_e.canonical_name) == substance_key(ing_s.canonical_name)


@pytest.fixture
def chat_client():
    from app import app
    return TestClient(app)


@pytest.mark.parametrize("llm_enabled", ["false", "true"])
def test_chat_e120_hindu_vegetarian_llm_modes(chat_client, monkeypatch, llm_enabled):
    """Live chat path: e120 must never appear in both Avoid and Safe (LLM on or off)."""
    monkeypatch.setenv("LLM_ENABLED", llm_enabled)
    import core.config as cfg

    monkeypatch.setattr(cfg, "llm_enabled", lambda: llm_enabled == "true")

    r = chat_client.post(
        "/chat/grocery",
        json={
            "query": "e120",
            "user_id": f"scenario-e120-llm-{llm_enabled}",
            "userProfile": {
                "dietary_preference": "Hindu Vegetarian",
                "allergens": [],
                "lifestyle": [],
            },
        },
    )
    assert r.status_code == 200, r.text[:400]
    audit = _extract_audit(r.text)
    assert audit is not None, "Missing INGREDIENT_AUDIT block"
    _assert_no_avoid_safe_overlap(audit)
    avoid = _group_names(audit, "avoid")
    safe = _group_names(audit, "safe")
    assert len(avoid) >= 1
    assert safe == []
    assert audit.get("summary", "").startswith("0 Safe")
    expl = audit.get("explanation", "").lower()
    assert "fine for your diet" not in expl
    assert "is not suitable" in expl or "not suitable" in expl or llm_enabled == "true"


@pytest.mark.parametrize("llm_enabled", ["false", "true"])
def test_chat_mixed_list_llm_modes(chat_client, monkeypatch, llm_enabled):
    monkeypatch.setenv("LLM_ENABLED", llm_enabled)
    import core.config as cfg

    monkeypatch.setattr(cfg, "llm_enabled", lambda: llm_enabled == "true")

    r = chat_client.post(
        "/chat/grocery",
        json={
            "query": "e441, sugar, salt",
            "user_id": f"scenario-mixed-llm-{llm_enabled}",
            "userProfile": {
                "dietary_preference": "Vegetarian",
                "allergens": [],
                "lifestyle": [],
            },
        },
    )
    assert r.status_code == 200
    audit = _extract_audit(r.text)
    assert audit is not None
    _assert_no_avoid_safe_overlap(audit)
    safe = _group_names(audit, "safe")
    assert any("sugar" in s.lower() for s in safe)
    assert any("salt" in s.lower() for s in safe)


@pytest.mark.parametrize(
    "query",
    ["e130", "e1222", "safnaksjnf", "xyznonexistent123"],
)
def test_unknown_inputs_never_false_safe_with_api(query):
    """Unknown E-numbers, invalid codes, and gibberish must not be marked Safe."""
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
    from core.models.verdict import VerdictStatus

    profile = _Profile(dietary_preference="Hindu Vegetarian")
    rids = user_profile_model_to_restriction_ids(profile)
    verdict = run_new_engine_chat(
        [query], user_profile=profile, restriction_ids=rids, use_api_fallback=True,
    )
    payload = build_ingredient_audit_payload(verdict=verdict, profile=profile, ingredients=[query])
    safe = _group_names(payload, "safe")
    assert verdict.status != VerdictStatus.SAFE, f"{query} incorrectly SAFE"
    assert safe == [], f"{query} incorrectly in Safe group: {safe}"
    assert payload["summary"].startswith("0 Safe"), payload["summary"]


def test_e120_still_avoid_with_api_fallback():
    """Known E-number in ontology must still Avoid when restricted."""
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
    from core.models.verdict import VerdictStatus

    profile = _Profile(dietary_preference="Hindu Vegetarian")
    rids = user_profile_model_to_restriction_ids(profile)
    verdict = run_new_engine_chat(
        ["e120"], user_profile=profile, restriction_ids=rids, use_api_fallback=True,
    )
    payload = build_ingredient_audit_payload(verdict=verdict, profile=profile, ingredients=["e120"])
    assert verdict.status == VerdictStatus.NOT_SAFE
    assert _group_names(payload, "avoid") == ["E120 · Carmine"]
    assert _group_names(payload, "safe") == []


def test_chat_unknown_e130_not_safe_llm_modes(chat_client, monkeypatch):
    """Live chat: e130 must land in Depends, not Safe (LLM on or off)."""
    import core.config as cfg

    for llm_on in (False, True):
        monkeypatch.setenv("LLM_ENABLED", "true" if llm_on else "false")
        monkeypatch.setattr(cfg, "llm_enabled", lambda v=llm_on: v)
        r = chat_client.post(
            "/chat/grocery",
            json={
                "query": "e130",
                "user_id": f"scenario-e130-llm-{llm_on}",
                "userProfile": {
                    "dietary_preference": "Hindu Vegetarian",
                    "allergens": [],
                    "lifestyle": [],
                },
            },
        )
        assert r.status_code == 200
        audit = _extract_audit(r.text)
        assert audit is not None
        safe = _group_names(audit, "safe")
        assert safe == [], f"e130 in Safe with LLM={llm_on}: {safe}"
        assert audit["summary"].startswith("0 Safe")
        expl = (audit.get("explanation") or "").lower()
        assert "all ingredients are suitable" not in expl
        assert "safe for consumption" not in expl


def test_safe_count_matches_audit_groups():
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids

    profile = _Profile(dietary_preference="Vegan")
    rids = user_profile_model_to_restriction_ids(profile)
    ingredients = ["milk", "sugar", "salt", "e120"]
    verdict = run_new_engine_chat(
        ingredients, user_profile=profile, restriction_ids=rids, use_api_fallback=False,
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict, profile=profile, ingredients=ingredients,
    )
    safe_names = _group_names(payload, "safe")
    assert len(safe_names) == count_safe_audit_ingredients(ingredients, verdict)
    summary_safe = int(payload["summary"].split(",")[0].strip().split()[0])
    assert summary_safe == len(safe_names)
