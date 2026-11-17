"""Jain must not firm-SAFE root vegetables after L2 first-wins collision fix.

Weak plural/alias records (parsnips, carrots, onions, potatoes, suran) used to
win the L2 index and leave root_vegetable false → Jain SAFE. Data patch sets
root_vegetable true on those ids; these forms must stay non-SAFE.
"""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.ike2.stores import local_ontology

_FORMS = (
    "parsnip",
    "parsnips",
    "carrot",
    "carrots",
    "onion",
    "onions",
    "potato",
    "potatoes",
    "suran",
    "elephant foot yam",
)


@pytest.fixture(autouse=True)
def _reset_l2():
    local_ontology.reset_cache()
    yield
    local_ontology.reset_cache()


@pytest.mark.parametrize("form", _FORMS)
def test_jain_root_veg_collision_forms_not_safe(form: str):
    status = evaluate_ingredients([form], ["jain"], use_api_fallback=False).status.value
    assert status != "SAFE", (form, status)
