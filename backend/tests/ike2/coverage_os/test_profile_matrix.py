from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS


def test_matrix_covers_supported_profiles_for_one_atom():
    rows = run_matrix("sugar", restriction_ids=sorted(SUPPORTED_RESTRICTIONS)[:3])
    profiles = {r["profile"] for r in rows}
    assert len(profiles) == 3
    assert all("chain" in r and "bucket" in r for r in rows)
    sugar_rows = [r for r in rows if r["ingredient"] == "sugar"]
    assert sugar_rows
    for r in sugar_rows:
        assert r["bucket"] in ("Safe", "Avoid", "Depends")
        assert r["chain"]["atom"]
        assert r["bucket"] == r["chain"]["verdict"]


def test_avoid_parity_beef_fails_veg_profiles():
    rows = run_matrix("beef", restriction_ids=["hindu_vegetarian", "vegan", "vegetarian"])
    by_p = {r["profile"]: r["bucket"] for r in rows}
    assert by_p["hindu_vegetarian"] == "Avoid"
    assert by_p["vegan"] == "Avoid"
    assert by_p["vegetarian"] == "Avoid"


def test_run_matrix_clears_resolution_cache(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.resolution_cache.clear",
        lambda: calls.append("resolution"),
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.local_ontology.reset_cache",
        lambda: calls.append("ontology"),
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.reset_variant_alias_cache",
        lambda: calls.append("aliases"),
    )
    run_matrix("sugar", restriction_ids=["vegan"])
    assert calls == ["resolution", "ontology", "aliases"]
    calls.clear()
    run_matrix("sugar", restriction_ids=["vegan"], clear_caches=False)
    assert calls == []
