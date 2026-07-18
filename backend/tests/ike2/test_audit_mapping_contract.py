from core.bridge import run_new_engine_chat
from core.models.verdict import VerdictStatus


def test_egg_hindu_non_veg_not_in_triggered():
    v = run_new_engine_chat(["egg"], restriction_ids=["hindu_non_vegetarian"])
    assert "egg" not in (v.triggered_ingredients or [])
    assert v.status != VerdictStatus.NOT_SAFE or not v.triggered_ingredients


def test_egg_hindu_non_veg_is_safe_not_depends():
    """egg_source is not unknown cow/pig species — HNV must firm-SAFE egg."""
    from core.models.verdict import VerdictStatus

    v = run_new_engine_chat(["egg"], restriction_ids=["hindu_non_vegetarian"])
    assert v.status == VerdictStatus.SAFE
    assert not (v.triggered_ingredients or [])
    assert "egg" not in (v.uncertain_ingredients or [])


def test_warn_compound_goes_to_uncertain_not_safe_path():
    v = run_new_engine_chat(["natural flavors"], restriction_ids=["vegan"])
    assert "natural flavors" in (v.uncertain_ingredients or [])
    assert "natural flavors" not in (v.triggered_ingredients or [])
