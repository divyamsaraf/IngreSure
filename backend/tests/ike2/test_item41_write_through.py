"""Item 41: reviewed write-through — no read-time L3 OR; name-keyed L3→L2 drift."""
from __future__ import annotations

from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.stores import local_ontology as lo
from core.normalization.normalizer import normalize_ingredient_key
from scripts.check_l2_l3_name_drift import (
    VERDICT_FLAGS,
    l2_flags_by_name,
    name_keyed_l3_l2_drift,
)


def test_name_keyed_drift_detects_l3_true_missing_from_l2():
    l2 = {"milk": {"dairy_source": False, "egg_source": False}}
    l3 = [{"canonical_name": "milk", "dairy_source": True, "egg_source": False, "source": "usda"}]
    drifted = name_keyed_l3_l2_drift(l3, l2, flags=("dairy_source", "egg_source"))
    assert drifted == [("milk", "dairy_source", "usda")]


def test_name_keyed_drift_ignores_l3_only_names():
    """Write-through applies to ontology-named rows; L3-only names are not L2 drift."""
    drifted = name_keyed_l3_l2_drift(
        [{"canonical_name": "unmapped xyz", "dairy_source": True, "source": "db"}],
        {},
        flags=("dairy_source",),
    )
    assert drifted == []


def test_name_keyed_drift_empty_when_l2_already_true():
    l2 = {"milk": {"dairy_source": True}}
    l3 = [{"canonical_name": "Milk", "dairy_source": True, "source": "db"}]
    assert name_keyed_l3_l2_drift(l3, l2, flags=("dairy_source",)) == []


def test_l2_index_is_name_keyed():
    idx = l2_flags_by_name()
    assert idx
    fibre = idx.get(normalize_ingredient_key("dietary fibre"))
    assert fibre is not None
    assert "sesame_source" in fibre


def test_replay_helper_flags_cover_allergen_and_animal_origin():
    assert "sesame_source" in VERDICT_FLAGS
    assert "animal_origin" in VERDICT_FLAGS
    assert "dairy_source" in VERDICT_FLAGS


def test_l2_hit_does_not_consult_or_or_l3(monkeypatch):
    """No blind read-time OR: an L2 hit must never merge L3 flags."""
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.truth_anchor as truth_anchor

    cache.clear()
    lo.reset_cache()
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("L3 must not run when L2 hits")

    # Force a name that misses L1 but hits L2.
    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(db, "resolve_alias", boom)
    monkeypatch.setattr(db, "disambiguate", boom)

    fact = lo.lookup(normalize_ingredient_key("dietary fibre"))
    assert fact is not None
    r = resolve("dietary fibre", None)
    assert r.status == "resolved"
    assert r.resolution_layer == "L2_local_ontology"
    assert called["n"] == 0
    # L3 extras must not appear: resolver returns the L2 fact as-is.
    assert r.group is fact or r.group.canonical_name == fact.canonical_name


def test_l2_hit_does_not_or_injected_l3_trues(monkeypatch):
    """Even if L3 would return extra trues, L2 resolution must not OR them in."""
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.truth_anchor as truth_anchor

    cache.clear()
    lo.reset_cache()
    l3_row = SimpleNamespace(
        canonical_name="dietary fibre",
        animal_origin=True,
        dairy_source=True,
        sesame_source=True,
        uncertainty_flags=[],
    )
    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(db, "disambiguate", lambda *_a, **_k: "none")
    monkeypatch.setattr(db, "resolve_alias", lambda *_a, **_k: l3_row)

    r = resolve("dietary fibre", None)
    assert r.resolution_layer == "L2_local_ontology"
    flags = dict(getattr(r.group, "flags", {}) or {})
    assert flags.get("dairy_source") is not True
    assert flags.get("sesame_source") is not True
