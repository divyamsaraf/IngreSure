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
