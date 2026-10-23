"""Legacy profile keys must become notices, never silently drop."""
from core.models.user_profile import UserProfile


def test_unknown_dietary_key_kept_and_noticed():
    p = UserProfile.from_dict(
        {"user_id": "test_u", "dietary_preference": "Raw Till 4", "allergens": [], "lifestyle": []}
    )
    assert p.dietary_preference == "Raw Till 4"
    notices = p.unsupported_notices()
    assert notices
    assert any("Raw Till 4" in n for n in notices)


def test_unknown_allergen_kept_and_noticed():
    p = UserProfile.from_dict(
        {
            "user_id": "test_u",
            "dietary_preference": "No rules",
            "allergens": ["Peanuts", "Nightshade"],
            "lifestyle": [],
        }
    )
    assert "Nightshade" in p.allergens
    assert "Peanuts" in p.allergens
    assert any("Nightshade" in n for n in p.unsupported_notices())
    assert not any("Peanuts" in n for n in p.unsupported_notices())


def test_legacy_restrictions_list_is_not_dropped():
    p = UserProfile.from_dict(
        {
            "user_id": "test_u",
            "restrictions": ["peanut_allergy", "mystery_diet"],
        }
    )
    notices = p.unsupported_notices()
    assert any("peanut_allergy" in n or "Peanuts" in p.allergens for n in notices) or "Peanuts" in p.allergens
    assert any("mystery_diet" in n for n in notices)
    dumped = p.to_dict()
    assert "mystery_diet" in json_blob(dumped)


def json_blob(d: dict) -> str:
    import json

    return json.dumps(d)


def test_to_dict_surfaces_unsupported_notices():
    p = UserProfile.from_dict({"user_id": "test_u", "dietary_preference": "Carnivore"})
    body = p.to_dict()
    assert body["unsupported_notices"]
    assert body["dietary_preference"] == "Carnivore"
