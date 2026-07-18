"""Three-tier resolution: ResolutionCache boot-seed, lazy Tier-2, silent Tier-3
degrade (design §9.4-9.6). Supabase errors and malformed Tier-3 rows must never
raise into chat and must never be invented as SAFE.
"""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache, resolver


def setup_function(_fn):
    # The cache is a process-lifetime singleton (design §9.5 invariant 4); tests
    # must not leak resolved/cached state between cases.
    resolution_cache.clear()


def test_sugar_resolves_when_db_raises():
    """Tier 1 (bundled core anchor) must answer with Supabase fully down."""
    import core.knowledge.ike2.stores.db as db

    def _raise(*_a, **_k):
        raise RuntimeError("down")

    orig_alias, orig_disambig = db.resolve_alias, db.disambiguate
    db.resolve_alias = _raise
    db.disambiguate = _raise
    try:
        r = resolver.resolve("sugar", None)
    finally:
        db.resolve_alias, db.disambiguate = orig_alias, orig_disambig

    assert r.status == "resolved"
    assert r.trusted is True
    assert r.resolution_layer == "L1_truth_anchor"


def test_unknown_when_all_tiers_miss_no_raise():
    """A token absent from every tier must degrade to uncertain, never raise."""
    import core.knowledge.ike2.stores.db as db

    def _raise(*_a, **_k):
        raise RuntimeError("down")

    orig_alias, orig_disambig = db.resolve_alias, db.disambiguate
    db.resolve_alias = _raise
    db.disambiguate = _raise
    try:
        r = resolver.resolve("zzzx_unknown_fixture_ingredient", None)
    finally:
        db.resolve_alias, db.disambiguate = orig_alias, orig_disambig

    assert r.status == "uncertain"
    assert r.trusted is False


def test_malformed_db_row_is_never_safe(monkeypatch):
    """A Tier-3 row that resolves successfully but is missing canonical_name /
    required flags must not be trusted enough to drive SAFE (design §9.4
    sanity-check: same incomplete-flags policy as Tier 2)."""
    import core.knowledge.ike2.stores.db as db

    bare_row = SimpleNamespace(ingredient_id="ghost-row")  # no canonical_name, no flags
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "unique")
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: bare_row)

    r = resolver.resolve("zzzx_malformed_fixture_ingredient", None)

    assert r.status == "uncertain" or r.trusted is False
    assert r.group is not bare_row


def test_repeat_lookup_serves_from_cache_without_hitting_db(monkeypatch):
    """Once a Tier-1 key is answered, a second lookup must not re-enter Supabase."""
    import core.knowledge.ike2.stores.db as db

    calls = []

    def _track(*a, **k):
        calls.append(a)
        raise RuntimeError("should not be called for a Tier-1 key")

    monkeypatch.setattr(db, "resolve_alias", _track)
    monkeypatch.setattr(db, "disambiguate", _track)

    first = resolver.resolve("chicken", None)
    second = resolver.resolve("chicken", None)

    assert first.status == "resolved"
    assert second.status == "resolved"
    assert calls == []


def test_tier2_local_ontology_hit_is_trusted_without_db(monkeypatch):
    """A staple present only in the Tier-2 local ontology (not Tier 1) must
    resolve without ever touching Supabase."""
    import core.knowledge.ike2.stores.db as db

    def _raise(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setattr(db, "resolve_alias", _raise)
    monkeypatch.setattr(db, "disambiguate", _raise)

    r = resolver.resolve("niacin", None)

    assert r.status == "resolved"
    assert r.trusted is True
    assert r.resolution_layer == "L2_local_ontology"
