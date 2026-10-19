"""Item 18: worker drains ike2_unknown_queue and writes ike2_* (never legacy)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.knowledge.ike2.resolver as resolver_mod
from core.external_apis.base import EnrichmentResult
from core.ontology.ingredient_schema import Ingredient
from tests.ike2.fake_supabase import FakeSupabase
from worker import tasks

_LEGACY_TABLES = {"unknown_ingredients", "ingredient_groups", "ingredients", "ingredient_aliases"}


def _queue_row(key="oat drink", freq=3, enrichment=None):
    return {"id": f"q-{key}", "normalized_key": key, "frequency": freq, "status": "pending",
            "enrichment": enrichment or {}}


@pytest.fixture
def fake(monkeypatch):
    fake = FakeSupabase({
        "ike2_unknown_queue": [_queue_row()],
        "unknown_ingredients": [{"id": "legacy-1", "normalized_key": "oat drink", "frequency": 9, "resolved": False}],
    })
    monkeypatch.setattr(tasks, "_get_db", lambda: SimpleNamespace(enabled=True, _client=fake))
    monkeypatch.setattr(tasks, "classify_ingredient_origin", lambda *_a, **_k: None)
    return fake


def _api(monkeypatch, ingredient, confidence="high", source="usda_fdc"):
    monkeypatch.setattr(
        tasks, "fetch_ingredient_from_apis",
        lambda _k, use_cache=True: EnrichmentResult(ingredient, confidence, source),
    )


def test_success_writes_ike2_discovered_and_resolves_queue(fake, monkeypatch):
    _api(monkeypatch, Ingredient(id="x", canonical_name="Oat beverage, unsweetened",
                                 plant_origin=True, gluten_source=True, aliases=["oat milk"]))

    out = tasks.enrich_unknown_batch()

    assert out["resolved"] == 1
    assert not (fake.touched() & _LEGACY_TABLES)
    assert fake.tables["unknown_ingredients"][0]["resolved"] is False

    [group] = fake.tables["ike2_ingredient_groups"]
    assert group["canonical_name"] == "oat drink"
    assert group["knowledge_state"] == "DISCOVERED"
    assert group["source"] == "enrichment_api"
    assert group["gluten_source"] is True

    aliases = {a["normalized_alias"] for a in fake.tables["ike2_aliases"]}
    assert aliases == {"oat drink"}

    [q] = fake.tables["ike2_unknown_queue"]
    assert q["status"] == "resolved"
    assert q["classification_decision"] == "enrichment_api:usda_fdc"
    assert q["enrichment"]["attempts"] == 1
    assert q["frequency"] == 3


def test_positive_hazard_flag_persists_on_discovered_row(fake, monkeypatch):
    """DISCOVERED still FAILs on a true hazard flag (Item 34; see
    test_decay_compliance_interaction) — the flag must reach the row."""
    _api(monkeypatch, Ingredient(id="x", canonical_name="Whey", animal_origin=True,
                                 dairy_source=True, animal_species="cow"))
    tasks.enrich_unknown_batch()
    [group] = fake.tables["ike2_ingredient_groups"]
    assert group["knowledge_state"] == "DISCOVERED"
    assert group["dairy_source"] is True
    assert group["animal_origin"] is True


def test_no_result_stays_pending_then_exhausts(fake, monkeypatch):
    _api(monkeypatch, None, confidence="low", source="none")
    for i in range(1, tasks.MAX_ATTEMPTS):
        tasks.enrich_unknown_batch()
        q = fake.tables["ike2_unknown_queue"][0]
        assert q["status"] == "pending"
        assert q["enrichment"]["attempts"] == i
    tasks.enrich_unknown_batch()
    q = fake.tables["ike2_unknown_queue"][0]
    assert q["status"] == "exhausted"
    assert "ike2_ingredient_groups" not in fake.tables
    assert not (fake.touched() & _LEGACY_TABLES)


def test_low_confidence_is_not_written(fake, monkeypatch):
    _api(monkeypatch, Ingredient(id="x", canonical_name="oat", plant_origin=True), confidence="low")
    tasks.enrich_unknown_batch()
    assert "ike2_ingredient_groups" not in fake.tables
    assert fake.tables["ike2_unknown_queue"][0]["status"] == "pending"


def test_validation_reject_is_quarantined_on_queue_row(fake, monkeypatch):
    _api(monkeypatch, Ingredient(id="x", canonical_name="mystery", animal_origin=True, plant_origin=True))
    out = tasks.enrich_unknown_batch()
    assert out["rejected"] == 1
    assert "ike2_ingredient_groups" not in fake.tables
    q = fake.tables["ike2_unknown_queue"][0]
    assert q["status"] == "rejected"
    assert q["enrichment"]["reject"]["violated_constraint"] == "dual_origin_requires_uncertainty"


def test_only_pending_rows_are_processed(fake, monkeypatch):
    fake.tables["ike2_unknown_queue"][0]["status"] = "resolved"
    _api(monkeypatch, Ingredient(id="x", canonical_name="oat", plant_origin=True))
    assert tasks.enrich_unknown_batch()["processed"] == 0


def test_product_batch_uses_ike2_resolver(monkeypatch):
    def _fake_resolve(token, region):
        if token == "sugar":
            return SimpleNamespace(status="resolved", resolution_layer="L1_truth_anchor")
        return SimpleNamespace(status="uncertain", resolution_layer="L5_unknown_queue")

    monkeypatch.setattr(resolver_mod, "resolve", _fake_resolve)
    out = tasks.process_product_ingredients_batch(["sugar, zzqx gum"])
    assert out == {"resolved": 1, "enqueued": 1, "strings_processed": 1}
