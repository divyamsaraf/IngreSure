"""Item 33 Prompt 3: /api/v1 resolve routes serve IKE-2 (evaluate untouched)."""
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import app
from core.knowledge.ike2 import resolver as resolver_mod
from core.knowledge.ike2 import unknown_queue as uq
from core.knowledge.ike2.truth_anchor import TruthAnchorFact
from tests.ike2.fake_supabase import FakeSupabase

client = TestClient(app)


def _miss_tiers(monkeypatch):
    monkeypatch.setattr(resolver_mod.truth_anchor, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.local_ontology, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.db, "disambiguate", lambda *_a, **_k: "none")
    monkeypatch.setattr(resolver_mod.db, "resolve_alias", lambda *_a, **_k: None)


def _queue(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase()
    monkeypatch.setattr(uq, "_default_client", lambda: fake)
    monkeypatch.setattr(uq, "_executor", None)
    return fake


def _drain_queue():
    if uq._executor is not None:
        uq._executor.shutdown(wait=True)


def test_post_resolve_tier1_truth_anchor():
    r = client.post("/api/v1/resolve-ingredient", json={"name": "milk", "try_api": True})
    assert r.status_code == 200
    body = r.json()
    assert body["knowledge_source"] == "truth_anchor"
    assert body["source_layer"] == "static"
    assert body["knowledge_state"] == "LOCKED"
    assert body["ingredient"]["canonical_name"] == "milk"
    assert body["ingredient"]["dairy_source"] is True
    assert body["ingredient"]["animal_origin"] is True


def test_post_resolve_tier2_local_ontology(monkeypatch):
    fact = TruthAnchorFact(
        canonical_name="xqz oat flake",
        flags={"plant_origin": True, "gluten_source": True},
        knowledge_state="AUTO_CLASSIFIED",
    )
    monkeypatch.setattr(resolver_mod.truth_anchor, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.local_ontology, "lookup", lambda n: fact if n == "xqz oat flake" else None)
    monkeypatch.setattr(resolver_mod.db, "disambiguate", lambda *_a, **_k: "none")
    monkeypatch.setattr(resolver_mod.db, "resolve_alias", lambda *_a, **_k: None)

    r = client.post("/api/v1/resolve-ingredient", json={"name": "xqz oat flake"})
    assert r.status_code == 200
    body = r.json()
    assert body["knowledge_source"] == "local_ontology"
    assert body["source_layer"] == "static"
    assert body["knowledge_state"] == "AUTO_CLASSIFIED"
    assert body["ingredient"]["gluten_source"] is True


def test_get_resolve_tier3_db(monkeypatch):
    group = SimpleNamespace(
        id="g-3",
        canonical_name="xqz whey",
        knowledge_state="DISCOVERED",
        animal_origin=True,
        dairy_source=True,
        plant_origin=False,
        uncertainty_flags=[],
    )
    monkeypatch.setattr(resolver_mod.truth_anchor, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.local_ontology, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.db, "disambiguate", lambda *_a, **_k: "unique")
    monkeypatch.setattr(resolver_mod.db, "resolve_alias", lambda *_a, **_k: group)

    r = client.get("/api/v1/ingredient/xqz%20whey")
    assert r.status_code == 200
    body = r.json()
    assert body["source_layer"] == "dynamic"
    assert body["knowledge_source"] == "db"
    assert body["knowledge_state"] == "DISCOVERED"
    assert body["ingredient"]["dairy_source"] is True
    assert body["ingredient"]["id"] == "g-3"


def test_miss_enqueues_ike2_not_legacy_even_if_log_unknown_false(monkeypatch):
    _miss_tiers(monkeypatch)
    fake = _queue(monkeypatch)
    legacy = []
    monkeypatch.setattr(
        "core.knowledge.ingredient_db.IngredientKnowledgeDB.upsert_unknown_ingredient",
        lambda *a, **k: legacy.append(a),
    )
    monkeypatch.setattr(
        "core.enrichment.unknown_log.log_unknown_ingredient",
        lambda *a, **k: legacy.append(a),
    )

    r = client.post(
        "/api/v1/resolve-ingredient",
        json={"name": "zzqx novel gum 33", "try_api": True, "log_unknown": False},
    )
    _drain_queue()
    assert r.status_code == 200
    body = r.json()
    assert body["ingredient"] is None
    assert body["knowledge_state"] == "UNCLASSIFIED"
    assert body["source_layer"] == "unknown"
    assert legacy == []
    assert "unknown_ingredients" not in fake.touched()
    rows = fake.tables[uq.TABLE]
    assert rows[0]["normalized_key"] == "zzqx novel gum 33"
    assert rows[0]["status"] == "pending"


def test_try_api_does_not_call_external_fetcher(monkeypatch):
    _miss_tiers(monkeypatch)
    _queue(monkeypatch)

    def _boom(*_a, **_k):
        raise AssertionError("resolve HTTP must not call external APIs")

    monkeypatch.setattr("core.external_apis.fetcher.fetch_ingredient_from_apis", _boom)
    monkeypatch.setattr("core.external_apis.fetcher.enrich_unknown_ingredient", _boom)
    r = client.post(
        "/api/v1/resolve-ingredient",
        json={"name": "zzqx no api 33", "try_api": True},
    )
    _drain_queue()
    assert r.status_code == 200
    assert r.json()["source_layer"] == "unknown"


def test_junk_key_miss_does_not_enqueue(monkeypatch):
    _miss_tiers(monkeypatch)
    fake = _queue(monkeypatch)
    r = client.post("/api/v1/resolve-ingredient", json={"name": "a"})
    _drain_queue()
    assert r.status_code == 200
    assert r.json()["ingredient"] is None
    assert fake.calls == []


def test_get_empty_name_still_400():
    r = client.get("/api/v1/ingredient/%20")
    assert r.status_code == 400
