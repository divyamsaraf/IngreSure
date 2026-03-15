"""
Full chat flow tests: multiple messages in sequence (greeting, ingredient queries, profiles).
Verifies stream tags, INGREDIENT_AUDIT structure, and verdict content. Works with or without Redis.
"""
import json
import pytest
from fastapi.testclient import TestClient

from core.stream_tags import PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG, PROFILE_REQUIRED_TAG


def _stream_has_tag(body: str, tag: str) -> bool:
    return tag in body


def _extract_audit_payload(body: str):
    """Parse first <<<INGREDIENT_AUDIT>>>...<<<INGREDIENT_AUDIT>>> block."""
    start = body.find(INGREDIENT_AUDIT_TAG)
    if start == -1:
        return None
    end = body.find(INGREDIENT_AUDIT_TAG, start + len(INGREDIENT_AUDIT_TAG))
    if end == -1:
        return None
    raw = body[start + len(INGREDIENT_AUDIT_TAG) : end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def test_flow_greeting_then_ingredient_queries():
    """Sequence: greeting → milk (vegan) → egg (vegan) → same user, all streams valid."""
    from app import app

    client = TestClient(app)
    user_id = "flow-multi-msg-user"

    # 1. Greeting
    r1 = client.post("/chat/grocery", json={"query": "hello", "user_id": user_id})
    assert r1.status_code == 200, r1.text[:300]
    assert _stream_has_tag(r1.text, PROFILE_UPDATE_TAG)
    assert len(r1.text.strip()) >= 10

    # 2. Ingredient: milk for vegan
    r2 = client.post(
        "/chat/grocery",
        json={
            "query": "Is milk vegan?",
            "user_id": user_id,
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    assert r2.status_code == 200, r2.text[:300]
    assert _stream_has_tag(r2.text, INGREDIENT_AUDIT_TAG)
    assert _stream_has_tag(r2.text, PROFILE_UPDATE_TAG)
    audit = _extract_audit_payload(r2.text)
    assert audit is not None
    assert "groups" in audit
    # Verdict text should mention milk or dairy
    assert "milk" in r2.text.lower() or "dairy" in r2.text.lower()

    # 3. Another ingredient: egg for vegan (same user)
    r3 = client.post(
        "/chat/grocery",
        json={
            "query": "Can I have egg?",
            "user_id": user_id,
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    assert r3.status_code == 200, r3.text[:300]
    assert _stream_has_tag(r3.text, INGREDIENT_AUDIT_TAG)
    assert _stream_has_tag(r3.text, PROFILE_UPDATE_TAG)
    audit3 = _extract_audit_payload(r3.text)
    assert audit3 is not None
    # Egg should be in avoid for vegan
    body_lower = r3.text.lower()
    assert "egg" in body_lower or "animal" in body_lower or "avoid" in body_lower

    # 4. Repeat milk (cache hit path when Redis enabled; same result either way)
    r4 = client.post(
        "/chat/grocery",
        json={
            "query": "What about milk?",
            "user_id": user_id,
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    assert r4.status_code == 200, r4.text[:300]
    assert _stream_has_tag(r4.text, INGREDIENT_AUDIT_TAG)
    audit4 = _extract_audit_payload(r4.text)
    assert audit4 is not None
    assert "milk" in r4.text.lower() or "dairy" in r4.text.lower()


def test_flow_jain_yam_and_onion():
    """Jain profile: yam and onion queries, audit has correct avoid/safe."""
    from app import app

    client = TestClient(app)
    user_id = "flow-jain-multi"

    # Set Jain profile
    r0 = client.post(
        "/profile",
        json={"user_id": user_id, "dietary_preference": "Jain", "allergens": [], "lifestyle": []},
    )
    assert r0.status_code == 200

    # Yam for Jain → avoid (root vegetable)
    r1 = client.post(
        "/chat/grocery",
        json={"query": "Is yam safe for me?", "user_id": user_id},
    )
    assert r1.status_code == 200, r1.text[:300]
    assert _stream_has_tag(r1.text, INGREDIENT_AUDIT_TAG)
    audit1 = _extract_audit_payload(r1.text)
    assert audit1 is not None
    avoid_names = []
    safe_names = []
    for g in audit1.get("groups") or []:
        for item in g.get("items") or []:
            name = (item.get("name") or "").lower()
            if g.get("status") == "avoid":
                avoid_names.append(name)
            if g.get("status") == "safe":
                safe_names.append(name)
    assert any("yam" in n or "sweet potato" in n for n in avoid_names)
    assert not any("yam" in n or "sweet potato" in n for n in safe_names)

    # Onion for Jain → avoid
    r2 = client.post(
        "/chat/grocery",
        json={"query": "Can I eat onion?", "user_id": user_id},
    )
    assert r2.status_code == 200, r2.text[:300]
    assert _stream_has_tag(r2.text, INGREDIENT_AUDIT_TAG)
    audit2 = _extract_audit_payload(r2.text)
    assert audit2 is not None
    avoid2 = []
    for g in audit2.get("groups") or []:
        if g.get("status") == "avoid":
            for item in g.get("items") or []:
                avoid2.append((item.get("name") or "").lower())
    assert any("onion" in n for n in avoid2)


def test_flow_greeting_does_not_overwrite_profile():
    """Greeting must not merge body.userProfile; server profile stays authoritative."""
    from app import app

    client = TestClient(app)
    user_id = "flow-greeting-profile-user"

    # Set profile to Jain via POST /profile
    r0 = client.post(
        "/profile",
        json={"user_id": user_id, "dietary_preference": "Jain", "allergens": [], "lifestyle": []},
    )
    assert r0.status_code == 200

    # Send "hi" with a different userProfile (Vegan); backend must not overwrite with Vegan
    r1 = client.post(
        "/chat/grocery",
        json={
            "query": "hi",
            "user_id": user_id,
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    assert r1.status_code == 200
    # Stream must contain PROFILE_UPDATE; the profile in it should be Jain (server), not Vegan
    assert _stream_has_tag(r1.text, PROFILE_UPDATE_TAG)
    start = r1.text.find(PROFILE_UPDATE_TAG) + len(PROFILE_UPDATE_TAG)
    end = r1.text.find(PROFILE_UPDATE_TAG, start)
    assert end != -1
    import json as _json
    payload = _json.loads(r1.text[start:end])
    diet = (payload.get("dietary_preference") or payload.get("diet") or "").strip()
    assert "Jain" in diet, f"Greeting must not overwrite profile; expected Jain, got {diet!r}"


def test_greeting_never_says_grocery_store(monkeypatch):
    """Greeting response (template path) must never say 'grocery store'."""
    from app import app

    monkeypatch.setattr("app.llm_compose_greeting", lambda profile: None)
    client = TestClient(app)
    user_id = "flow-greeting-wording-user"
    r = client.post(
        "/chat/grocery",
        json={
            "query": "hi",
            "user_id": user_id,
            "userProfile": {"dietary_preference": "Hindu Vegetarian", "allergens": [], "lifestyle": []},
        },
    )
    assert r.status_code == 200
    text = r.text
    for tag in (PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG):
        while tag in text:
            start = text.find(tag)
            end = text.find(tag, start + len(tag))
            if end != -1:
                text = text[:start] + text[end + len(tag) :]
            else:
                text = text[:start] + text[start + len(tag) :]
    assert "grocery store" not in text.lower(), f"Greeting must not say 'grocery store'; got: {text[:300]!r}"


def test_greeting_with_profile_uses_diet_specific_template(monkeypatch):
    """When profile is set (e.g. Hindu Vegetarian), greeting uses diet-specific template."""
    from app import app

    monkeypatch.setattr("app.llm_compose_greeting", lambda profile: None)
    client = TestClient(app)
    user_id = "flow-greeting-diet-user"
    client.post(
        "/profile",
        json={"user_id": user_id, "dietary_preference": "Hindu Vegetarian", "allergens": [], "lifestyle": []},
    )
    r = client.post("/chat/grocery", json={"query": "hi", "user_id": user_id})
    assert r.status_code == 200
    text = r.text
    for tag in (PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG):
        while tag in text:
            start = text.find(tag)
            end = text.find(tag, start + len(tag))
            if end != -1:
                text = text[:start] + text[end + len(tag) :]
            else:
                text = text[:start] + text[start + len(tag) :]
    text_lower = text.lower()
    assert "grocery store" not in text_lower
    assert "namaste" in text_lower or "hindu vegetarian" in text_lower


def test_template_greeting_all_diets():
    """Template greeting has correct wording for every dietary preference (no store language)."""
    from core.response_composer import compose_greeting

    class MockProfile:
        def __init__(self, dietary_preference: str):
            self.dietary_preference = dietary_preference

    diets = [
        "No rules",
        "Vegan",
        "Vegetarian",
        "Pescatarian",
        "Jain",
        "Halal",
        "Kosher",
        "Hindu Vegetarian",
        "Hindu Non Vegetarian",
    ]
    for diet in diets:
        profile = MockProfile(diet)
        msg = compose_greeting(profile)
        assert "grocery store" not in msg.lower(), f"Diet {diet!r}: must not say grocery store"
        assert "ingredient" in msg.lower(), f"Diet {diet!r}: should mention ingredient checking"
    # No profile
    msg_none = compose_greeting(None)
    assert "grocery store" not in msg_none.lower()
    assert "ingredient" in msg_none.lower()


def test_flow_profile_update_slash_then_ingredient():
    """Slash command /update then ingredient query."""
    from app import app

    client = TestClient(app)
    user_id = "flow-slash-user"

    r1 = client.post(
        "/chat/grocery",
        json={"query": "/update dietary_preference Vegan", "user_id": user_id},
    )
    assert r1.status_code == 200
    assert _stream_has_tag(r1.text, PROFILE_UPDATE_TAG)

    r2 = client.post(
        "/chat/grocery",
        json={"query": "Is honey vegan?", "user_id": user_id},
    )
    assert r2.status_code == 200
    assert _stream_has_tag(r2.text, INGREDIENT_AUDIT_TAG)
