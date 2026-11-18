"""#43 flip-blocking false-SAFE caps: framework-scoped L1 verdict_cap only."""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.ike2 import resolution_cache, resolver
from core.knowledge.ike2.keep_whole import clear_keep_whole_cache
from core.knowledge.ike2.stores import local_ontology

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
    "sulfite_sensitive",
)

_GLUTEN_FORMS = (
    "hing",
    "asafoetida",
    "asafetida",
    "papad",
    "papadum",
    "brewer's yeast",
    "brewers yeast",
)

_SULFITE_FORMS = (
    "dried apricots",
)


@pytest.fixture(autouse=True)
def _reset():
    resolution_cache.clear()
    local_ontology.reset_cache()
    clear_keep_whole_cache()
    yield
    resolution_cache.clear()
    local_ontology.reset_cache()
    clear_keep_whole_cache()


@pytest.mark.parametrize("form", _GLUTEN_FORMS)
def test_gluten_cap_forms_uncertain_on_gluten_free_only(form: str):
    got = {}
    for fw in _ALL_FRAMEWORKS:
        resolution_cache.clear()
        local_ontology.reset_cache()
        clear_keep_whole_cache()
        got[fw] = evaluate_ingredients([form], [fw], use_api_fallback=False).status.value
    assert got["gluten_free"] == "UNCERTAIN", (form, got["gluten_free"])
    # Hing / papad must stay Jain-clean; brewer's yeast stays fungal NOT_SAFE.
    if "yeast" in form:
        assert got["jain"] == "NOT_SAFE", (form, got["jain"])
    else:
        assert got["jain"] == "SAFE", (form, got["jain"])
    for fw, status in got.items():
        if fw in ("gluten_free", "jain", "alcohol_free"):
            continue
        assert status == "SAFE", (form, fw, status)


@pytest.mark.parametrize("form", _SULFITE_FORMS)
def test_dried_apricots_uncertain_on_sulfite_sensitive_only(form: str):
    got = {}
    for fw in _ALL_FRAMEWORKS:
        resolution_cache.clear()
        local_ontology.reset_cache()
        clear_keep_whole_cache()
        got[fw] = evaluate_ingredients([form], [fw], use_api_fallback=False).status.value
    assert got["sulfite_sensitive"] == "UNCERTAIN", (form, got["sulfite_sensitive"])
    for fw, status in got.items():
        if fw in ("sulfite_sensitive", "alcohol_free"):
            continue
        assert status == "SAFE", (form, fw, status)


def test_hing_scoped_cap_flags():
    r = resolver.resolve("hing", None)
    assert r.resolution_layer == "L1_truth_anchor"
    flags = r.group.flags
    assert flags.get("verdict_cap") == "WARN"
    assert flags.get("verdict_cap_restrictions") == ["gluten_free"]


def test_brewers_yeast_split_from_plain_yeast():
    """Brewer's yeast must not share the uncapped plain-yeast L1 fact."""
    by = resolver.resolve("brewer's yeast", None)
    y = resolver.resolve("yeast", None)
    assert by.group.canonical_name == "brewer's yeast"
    assert y.group.canonical_name == "yeast"
    assert by.group.flags.get("verdict_cap_restrictions") == ["gluten_free"]
    assert y.group.flags.get("verdict_cap") in (None, "")
    assert evaluate_ingredients(["yeast"], ["gluten_free"], use_api_fallback=False).status.value == "SAFE"
