"""L3 chaos: DB down and missing view columns must degrade to UNCERTAIN, never SAFE."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import app
from core import degraded as deg
from core.knowledge.ike2 import resolution_cache, resolver
from core.models.verdict import VerdictStatus

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_BACKEND, ".env"))

client = TestClient(app, raise_server_exceptions=False)


def _has_local_db() -> bool:
    url = os.getenv("SUPABASE_URL") or ""
    return bool(url) and ("127.0.0.1" in url or "localhost" in url)


def setup_function(_fn):
    resolution_cache.clear()


def _tier3_atom_row(**extra):
    row = dict(
        canonical_name="zzzx_l3_chaos_row",
        animal_origin=False,
        plant_origin=True,
        ingredient_id="chaos",
        uncertainty_flags=[],
    )
    row.update(extra)
    return SimpleNamespace(**row)


def test_missing_source_column_is_uncertain_not_safe(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.stores.local_ontology as local_ontology
    import core.knowledge.ike2.truth_anchor as truth_anchor

    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(local_ontology, "lookup", lambda *_a, **_k: None)
    row = _tier3_atom_row(asserted_flags=[])
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "unique")
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: row)

    before = deg.snapshot()["count"]
    r = resolver.resolve("zzzx_l3_missing_source_atom", None)
    assert r.status == "uncertain"
    assert r.trusted is False
    assert r.group is None
    assert deg.snapshot()["count"] == before + 1


def test_missing_asserted_flags_column_is_uncertain_not_safe(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.stores.local_ontology as local_ontology
    import core.knowledge.ike2.truth_anchor as truth_anchor

    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(local_ontology, "lookup", lambda *_a, **_k: None)
    row = _tier3_atom_row(source="usda")
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "unique")
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: row)

    r = resolver.resolve("zzzx_l3_missing_asserted_flags_atom", None)
    assert r.status == "uncertain"
    assert r.trusted is False
    assert r.group is None


def test_db_down_resolve_is_uncertain_not_safe(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.stores.local_ontology as local_ontology
    import core.knowledge.ike2.truth_anchor as truth_anchor

    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(local_ontology, "lookup", lambda *_a, **_k: None)

    def _down(*_a, **_k):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(db, "disambiguate", _down)
    monkeypatch.setattr(db, "resolve_alias", _down)

    before = deg.snapshot()["count"]
    r = resolver.resolve("zzzx_l3_db_down_atom", None)
    assert r.status == "uncertain"
    assert r.trusted is False
    assert deg.snapshot()["count"] == before + 1


def test_health_db_down_is_uncertain_not_safe(monkeypatch):
    from core.knowledge.ike2 import audit_health

    monkeypatch.setattr(
        audit_health,
        "db_health",
        lambda: {
            "db_reachable": False,
            "ike2_status": VerdictStatus.UNCERTAIN.value,
            "degraded": {"count": 1},
        },
    )
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ike2_status") == VerdictStatus.UNCERTAIN.value
    assert body.get("db_reachable") is False
    assert str(body.get("ike2_status", "")).upper() != "SAFE"
    assert body.get("status") != "SAFE"


@pytest.mark.skipif(not _has_local_db(), reason="needs local supabase")
def test_chaos_local_db_down_probe_is_uncertain(monkeypatch):
    from core.knowledge.ike2 import audit_health
    from core.knowledge.ingredient_db import IngredientKnowledgeDB

    monkeypatch.setattr(IngredientKnowledgeDB, "ping", lambda self: False)
    monkeypatch.setattr(IngredientKnowledgeDB, "enabled", True)
    body = audit_health.db_health()
    assert body["db_reachable"] is False
    assert body["ike2_status"] == VerdictStatus.UNCERTAIN.value
    assert body["ike2_status"] != "SAFE"
