"""Emergency intent preempts the verdict flow."""
from fastapi.testclient import TestClient

from app import app
from core.emergency import detect_emergency, number_for_region
from core.stream_tags import INGREDIENT_AUDIT_TAG

client = TestClient(app, raise_server_exceptions=False)


def test_detect_emergency_call_911():
    hit = detect_emergency("Call 911 for me. Ingredients: water.")
    assert hit is not None
    assert hit.kind == "emergency"


def test_chat_emergency_no_audit():
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Call 911 for me. Ingredients: water.",
            "user_id": "emerg-1",
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    assert r.status_code == 200
    assert INGREDIENT_AUDIT_TAG not in r.text
    assert "911" in r.text


def test_cant_breathe_no_verdict():
    r = client.post(
        "/chat/grocery",
        json={
            "query": "I ate peanuts and I can't breathe. What do I do?",
            "user_id": "emerg-2",
            "userProfile": {"dietary_preference": "No rules", "allergens": ["peanuts"], "lifestyle": []},
        },
    )
    assert r.status_code == 200
    assert INGREDIENT_AUDIT_TAG not in r.text
    low = r.text.lower()
    assert "emergency" in low or "911" in r.text or "seek" in low or "call" in low


def test_region_numbers_table():
    assert number_for_region("US") == "911"
    assert number_for_region("GB") == "999"
    assert number_for_region("EU") == "112"
    assert number_for_region("AU") == "000"
    assert number_for_region("NZ") == "111"
    assert number_for_region("AE") == "998"
    assert number_for_region("IN") == "112"
