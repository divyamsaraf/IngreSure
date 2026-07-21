from types import SimpleNamespace

from core.knowledge.ike2.resolver import resolve


def _plant_gelatin():
    # A fake GroupRow as the DB might (wrongly) return it: gelatin as plant.
    return SimpleNamespace(
        canonical_name="gelatin",
        animal_origin=False,
        ingredient_id="fake",
        uncertainty_flags=[],
    )


def test_truth_anchor_overrides_db(monkeypatch):
    # even if DB says gelatin is plant, truth anchor wins
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: _plant_gelatin())
    r = resolve("gelatin", region=None)
    assert r.group.flags["animal_origin"] is True
    assert r.resolution_layer == "L1_truth_anchor"


def test_unknown_ingredient_is_uncertain_not_safe(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: None)
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "none")
    r = resolve("totally_unknown_xyz", region=None)
    assert r.status == "uncertain"


def test_ambiguous_alias_no_region_uncertain(monkeypatch):
    # An alias that misses Tier 1/2 and is region-ambiguous at Tier 3 must stay
    # uncertain. ("yam" is no longer usable here: it is statically canonicalized
    # to the Tier-1 root vegetable "elephant foot yam" for this India-context app.)
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "ambiguous")
    r = resolve("unmapped_ambiguous_alias", region=None)
    assert r.status == "uncertain"


def test_title_case_atom_uses_normalized_key_for_tier3(monkeypatch):
    """Chat lists send 'Beets'; DB aliases are stored as 'beets'."""
    import core.knowledge.ike2.resolution_cache as cache
    import core.knowledge.ike2.stores.db as db
    import core.knowledge.ike2.stores.local_ontology as local_ontology
    import core.knowledge.ike2.truth_anchor as truth_anchor

    cache.clear()
    monkeypatch.setattr(truth_anchor, "lookup", lambda *_a, **_k: None)
    monkeypatch.setattr(local_ontology, "lookup", lambda *_a, **_k: None)
    seen = {}

    def _disambiguate(alias, region):
        seen["disambiguate"] = alias
        return "none"

    def _resolve_alias(alias, region):
        seen["resolve_alias"] = alias
        return SimpleNamespace(
            canonical_name="beet",
            animal_origin=False,
            ingredient_id="beet",
            uncertainty_flags=[],
        )

    monkeypatch.setattr(db, "disambiguate", _disambiguate)
    monkeypatch.setattr(db, "resolve_alias", _resolve_alias)
    r = resolve("Beets", region=None)
    assert seen["disambiguate"] == "beet"
    assert seen["resolve_alias"] == "beet"
    assert r.status == "resolved"
    assert r.resolution_layer == "L3_db_alias"
