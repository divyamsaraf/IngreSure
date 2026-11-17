"""DRAFT #41 — Jain onion/root expansions (not opened until owner sign-off).

Covers Claude's confirmed-candidate list:
  onion_source: scallion (+ aliases scallions/green onions), ramps
  root_vegetable: cassava, jicama, horseradish, wasabi, galangal, chicory,
                  salsify, sunchokes, celeriac (new record, keeps celery_source)
"""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.ike2 import resolution_cache, resolver
from core.knowledge.ike2.stores import local_ontology

_ONION_FORMS = ("scallion", "scallions", "green onions", "ramps")
_ROOT_FORMS = (
    "cassava",
    "jicama",
    "horseradish",
    "wasabi",
    "galangal",
    "chicory root",
    "salsify",
    "sunchoke",
    "celeriac",
)


@pytest.fixture(autouse=True)
def _reset():
    resolution_cache.clear()
    local_ontology.reset_cache()
    yield
    resolution_cache.clear()
    local_ontology.reset_cache()


@pytest.mark.parametrize("form", _ONION_FORMS)
def test_jain_batch41_onion_forms_not_safe(form: str):
    status = evaluate_ingredients([form], ["jain"], use_api_fallback=False).status.value
    assert status != "SAFE", (form, status)


@pytest.mark.parametrize("form", _ROOT_FORMS)
def test_jain_batch41_root_forms_not_safe(form: str):
    status = evaluate_ingredients([form], ["jain"], use_api_fallback=False).status.value
    assert status != "SAFE", (form, status)


def test_celeriac_is_own_group_with_celery_and_root():
    r = resolver.resolve("celeriac", None)
    assert r.status == "resolved"
    assert r.resolution_layer in ("L1_truth_anchor", "L2_local_ontology")
    g = r.group
    cn = getattr(g, "canonical_name", None) or (g.get("canonical_name") if isinstance(g, dict) else None)
    assert cn == "celeriac"
    flags = getattr(g, "flags", None) or g
    assert bool(flags.get("root_vegetable")) is True
    assert bool(flags.get("celery_source")) is True


def test_celery_l1_no_longer_aliases_celeriac():
    r = resolver.resolve("celery", None)
    assert r.status == "resolved"
    g = r.group
    cn = getattr(g, "canonical_name", None) or (g.get("canonical_name") if isinstance(g, dict) else None)
    assert cn == "celery"
    celeriac = resolver.resolve("celeriac", None)
    cn2 = getattr(celeriac.group, "canonical_name", None) or (
        celeriac.group.get("canonical_name") if isinstance(celeriac.group, dict) else None
    )
    assert cn2 == "celeriac"
