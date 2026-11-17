"""Token-vs-flag sweep: beer gluten + Jain fermented L1→L2 aligns.

Confirmed false-SAFE hits from the L1∪L2 name-token lint (flip-blocking).
Excluded as false positives (token substring, not hazard): plant milks/butters,
cream of tartar, oyster mushrooms.
"""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.ike2 import resolution_cache, resolver
from core.knowledge.ike2.stores import local_ontology

# Frameworks checked in the before/after matrix (intended cells only may move).
_ALL_FRAMEWORKS = (
    "jain",
    "gluten_free",
    "vegan",
    "hindu_vegetarian",
    "halal",
    "kosher",
    "dairy_free",
    "soy_allergy",
    "fish_allergy",
    "shellfish_allergy",
    "egg_free",
    "peanut_allergy",
    "tree_nut_allergy",
    "sesame_allergy",
    "alcohol_free",
)

_BEER_FORMS = ("beer",)
_FERMENTED_JAIN_FORMS = (
    "soy sauce",
    "msg",
    "e621",
    "monosodium glutamate",
    "ajinomoto",
    "apple cider vinegar",
    "cider vinegar",
    "balsamic vinegar",
    "champagne vinegar",
    "chinkiang vinegar",
    "malt vinegar",
    "sherry vinegar",
)


@pytest.fixture(autouse=True)
def _reset():
    from core.knowledge.ike2.keep_whole import clear_keep_whole_cache

    resolution_cache.clear()
    local_ontology.reset_cache()
    clear_keep_whole_cache()
    yield
    resolution_cache.clear()
    local_ontology.reset_cache()
    clear_keep_whole_cache()


@pytest.mark.parametrize("form", _BEER_FORMS)
def test_beer_gluten_free_not_safe(form: str):
    status = evaluate_ingredients([form], ["gluten_free"], use_api_fallback=False).status.value
    assert status == "NOT_SAFE", (form, status)


@pytest.mark.parametrize("form", _BEER_FORMS)
def test_beer_has_gluten_source_flag(form: str):
    r = resolver.resolve(form, None)
    assert r.status == "resolved"
    flags = getattr(r.group, "flags", None) or r.group
    assert bool(flags.get("gluten_source")) is True


def test_soy_sauce_stays_keep_whole():
    """Recipe-tear would drop L1 fermented; keep-whole is required for Jain WARN."""
    from core.knowledge.ike2.keep_whole import clear_keep_whole_cache, is_keep_whole
    from core.normalization.parser import flatten_ingredients

    clear_keep_whole_cache()
    assert is_keep_whole("soy sauce") is True
    assert flatten_ingredients("soy sauce") == ["soy sauce"]


@pytest.mark.parametrize("form", _FERMENTED_JAIN_FORMS)
def test_fermented_jain_not_firm_safe(form: str):
    """Jain fermented rule is WARN → UNCERTAIN (never firm SAFE)."""
    status = evaluate_ingredients([form], ["jain"], use_api_fallback=False).status.value
    assert status != "SAFE", (form, status)


@pytest.mark.parametrize("form", _FERMENTED_JAIN_FORMS)
def test_fermented_flag_present(form: str):
    r = resolver.resolve(form, None)
    assert r.status == "resolved"
    flags = getattr(r.group, "flags", None) or r.group
    assert bool(flags.get("fermented")) is True, (form, flags.get("fermented"))


def test_beer_matrix_only_gluten_free_moves():
    """Non-gluten frameworks for beer stay at the pre-sweep expected values."""
    expected = {
        "jain": "NOT_SAFE",
        "gluten_free": "NOT_SAFE",
        "vegan": "SAFE",
        "hindu_vegetarian": "SAFE",
        "halal": "NOT_SAFE",
        "kosher": "SAFE",
        "dairy_free": "SAFE",
        "soy_allergy": "SAFE",
        "fish_allergy": "SAFE",
        "shellfish_allergy": "SAFE",
        "egg_free": "SAFE",
        "peanut_allergy": "SAFE",
        "tree_nut_allergy": "SAFE",
        "sesame_allergy": "SAFE",
        "alcohol_free": "UNCERTAIN",
    }
    got = {}
    for fw in _ALL_FRAMEWORKS:
        resolution_cache.clear()
        local_ontology.reset_cache()
        got[fw] = evaluate_ingredients(["beer"], [fw], use_api_fallback=False).status.value
    assert got == expected


@pytest.mark.parametrize(
    "form",
    (
        "soy sauce",
        "msg",
        "apple cider vinegar",
        "balsamic vinegar",
        "champagne vinegar",
    ),
)
def test_fermented_matrix_only_jain_moves(form: str):
    """Only the Jain column may leave SAFE; other frameworks stay put."""
    # Pre-sweep baselines (form-specific where they differed).
    baselines = {
        "soy sauce": {
            "gluten_free": "NOT_SAFE",
            "soy_allergy": "NOT_SAFE",
        },
        "msg": {},
        "apple cider vinegar": {},
        "balsamic vinegar": {},
        "champagne vinegar": {},
    }
    default_safe = {
        fw: "SAFE"
        for fw in _ALL_FRAMEWORKS
        if fw not in ("jain", "alcohol_free")
    }
    expected = {**default_safe, **baselines.get(form, {}), "alcohol_free": "UNCERTAIN"}
    # Jain: fermented WARN → not SAFE
    for fw, want in expected.items():
        resolution_cache.clear()
        local_ontology.reset_cache()
        got = evaluate_ingredients([form], [fw], use_api_fallback=False).status.value
        assert got == want, (form, fw, got, want)
    resolution_cache.clear()
    local_ontology.reset_cache()
    jain = evaluate_ingredients([form], ["jain"], use_api_fallback=False).status.value
    assert jain != "SAFE", (form, jain)
