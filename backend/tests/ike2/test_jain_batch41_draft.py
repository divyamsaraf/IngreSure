"""DRAFT #41 — Jain onion/root expansions (not opened until owner sign-off).

  onion_source: scallion (+ aliases scallions/green onions), ramps
  root_vegetable: cassava, jicama, horseradish, wasabi, galangal, salsify,
                  sunchokes, celeriac (new), chicory_root (new; leaf chicory untouched)
  salsify keeps asserted shellfish_source clear (vegetable oyster guard)
"""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.ike2 import resolution_cache, resolver
from core.knowledge.ike2.stores import local_ontology

_ONION_FORMS = ("scallion", "scallions", "green onions", "ramps")
_ROOT_FORMS = (
    "cassava",
    "manioc",
    "yuca",
    "jicama",
    "horseradish",
    "wasabi",
    "galangal",
    "chicory root",
    "salsify",
    "sunchoke",
    "jerusalem artichoke",
    "jerusalem artichokes",
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


def test_leaf_chicory_not_forced_root():
    r = resolver.resolve("chicory", None)
    assert r.status == "resolved"
    g = r.group
    flags = getattr(g, "flags", None) or g
    assert bool(flags.get("root_vegetable")) is False


def test_chicory_root_is_own_root_group():
    r = resolver.resolve("chicory root", None)
    assert r.status == "resolved"
    g = r.group
    cn = getattr(g, "canonical_name", None) or (g.get("canonical_name") if isinstance(g, dict) else None)
    assert cn in ("chicory root", "chicory_root")
    flags = getattr(g, "flags", None) or g
    assert bool(flags.get("root_vegetable")) is True


def test_celeriac_celery_allergy_not_safe():
    status = evaluate_ingredients(["celeriac"], ["celery_allergy"], use_api_fallback=False).status.value
    assert status == "NOT_SAFE"


def test_celeriac_jain_not_safe():
    status = evaluate_ingredients(["celeriac"], ["jain"], use_api_fallback=False).status.value
    assert status == "NOT_SAFE"


def test_celery_stalk_jain_safe():
    status = evaluate_ingredients(["celery stalk"], ["jain"], use_api_fallback=False).status.value
    assert status == "SAFE"


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


def test_salsify_keeps_asserted_shellfish_clear():
    from core.knowledge.ike2.etl.load_ontology import load_ontology_records
    from core.knowledge.ike2.etl.adapt import map_record
    from core.knowledge.ike2.etl.sources import canonical_source, default_knowledge_state
    raw = next(r for r in load_ontology_records() if r.get("id") == "salsify")
    assert raw.get("shellfish_source") is False
    assert "shellfish_source" in (raw.get("asserted_flags") or [])
    row, _ = map_record(raw, canonical_source("ontology"), default_knowledge_state(canonical_source("ontology")))
    assert row.get("shellfish_source") is False
    assert "shellfish_source" in (row.get("asserted_flags") or [])
