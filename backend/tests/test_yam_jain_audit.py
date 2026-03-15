"""Regression test: Jain + yam appears only in Avoid, not Safe."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("diet", ["Jain"])
def test_jain_yam_only_avoid_not_safe(diet):
    from app import app

    client = TestClient(app)
    user_id = "yam-jain-test-user"

    # Ensure profile is set to Jain
    r = client.post(
        "/profile",
        json={"user_id": user_id, "dietary_preference": diet, "allergens": [], "lifestyle": []},
    )
    assert r.status_code == 200

    # Chat about yam
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Is yam safe for me?",
            "user_id": user_id,
        },
    )
    assert r.status_code == 200
    body = r.text
    # Extract the INGREDIENT_AUDIT JSON block
    start = body.find("<<<INGREDIENT_AUDIT>>>")
    assert start != -1
    end = body.find("<<<INGREDIENT_AUDIT>>>", start + 1)
    assert end != -1
    import json

    audit_json = body[start + len("<<<INGREDIENT_AUDIT>>>") : end]
    payload = json.loads(audit_json)
    groups = payload.get("groups") or []
    avoid_names = []
    safe_names = []
    for g in groups:
        status = g.get("status")
        for item in g.get("items") or []:
            name = (item.get("name") or "").lower()
            if status == "avoid":
                avoid_names.append(name)
            if status == "safe":
                safe_names.append(name)

    # Yam (or its canonical) must appear in Avoid
    assert any("yam" in n or "sweet potato" in n for n in avoid_names)
    # Yam must not appear in Safe
    assert not any("yam" in n or "sweet potato" in n for n in safe_names)

