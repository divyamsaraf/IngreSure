# backend/tests/ike2/coverage_os/test_neutralize_keep_fallback.py
from unittest.mock import patch

from core.knowledge.ike2.coverage_os.neutralize import apply_policies


def test_culinary_keep_wine_vinegar_no_wine_tear():
    roles = {"vinegar": "culinary_keep"}
    r = apply_policies("wine vinegar", role_index=roles, lookup_flags=lambda t: None)
    assert r.atoms == ["wine vinegar"]
    assert "wine" not in r.atoms
    assert "culinary_keep" in r.policy_fired


def test_process_keep_emits_phrase_and_base():
    roles = {"mechanically": "process_keep", "separated": "process_keep"}
    flags = {"chicken": {"animal_origin": True, "animal_species": "chicken"}}
    r = apply_policies(
        "mechanically separated chicken",
        role_index=roles,
        lookup_flags=lambda t: flags.get(t),
    )
    assert "mechanically separated chicken" in r.atoms
    assert "chicken" in r.atoms
    assert r.derived_from.get("chicken") == "mechanically separated chicken"
    assert "process_keep" in r.policy_fired


def test_tier1_fallback_keep_when_no_role():
    roles = {}
    fake = object()
    with patch(
        "core.knowledge.ike2.coverage_os.neutralize.truth_anchor_lookup",
        return_value=fake,
    ):
        r = apply_policies("fish oil", role_index=roles, lookup_flags=lambda t: None)
    assert r.atoms == ["fish oil"]
    assert "tier1_keep" in r.policy_fired


def test_no_role_no_tier1_passthrough_garlic_pasta():
    """No-policy default is passthrough — NOT keyword tear inside neutralize."""
    roles = {}
    with patch(
        "core.knowledge.ike2.coverage_os.neutralize.truth_anchor_lookup",
        return_value=None,
    ):
        r = apply_policies(
            "garlic pasta",
            role_index=roles,
            lookup_flags=lambda t: None,
        )
    assert r.atoms == ["garlic pasta"]
    assert r.policy_fired == []
    assert r.derived_from == {}
