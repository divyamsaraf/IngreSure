from core.observability.scrub import REDACTED, drop_request_bodies, scrub_value


def test_scrub_redacts_ingredient_and_profile_fields():
    raw = {
        "route": "/chat/grocery",
        "query": "milk, peanuts",
        "userProfile": {"dietary_preference": "Vegan", "allergens": ["Peanut"]},
        "status": 200,
    }
    out = scrub_value(raw)
    assert out["route"] == "/chat/grocery"
    assert out["status"] == 200
    assert out["query"] == REDACTED
    assert out["userProfile"] == REDACTED


def test_drop_request_bodies_strips_data_and_auth():
    event = {
        "request": {
            "url": "https://api.example/chat/grocery",
            "data": {"query": "gelatin"},
            "headers": {"Authorization": "Bearer secret", "X-Request-ID": "abc"},
        },
        "user": {"id": "u1", "email": "a@b.c", "ip_address": "1.2.3.4"},
        "extra": {"ingredients_text": "milk"},
    }
    out = drop_request_bodies(event)
    assert "data" not in out["request"]
    assert out["request"]["headers"]["Authorization"] == REDACTED
    assert out["request"]["headers"]["X-Request-ID"] == "abc"
    assert out["extra"]["ingredients_text"] == REDACTED
