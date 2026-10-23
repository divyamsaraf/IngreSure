from pathlib import Path

from scripts.seed_prod import ALLOWED_L1, FORBIDDEN, _REPO, plan_sources


def test_default_plan_is_ontology_plus_allowlisted_l1():
    plan = plan_sources([])
    names = [p["source"] for p in plan]
    assert names[0] == "ontology"
    assert set(names[1:]) <= ALLOWED_L1
    assert "produce_catalog" in names
    assert "animal_catalog" in names
    assert "infoods" in names


def test_forbidden_sources_rejected():
    for src in ("unknown_queue", "shadow", "usda", "fssai", "staples", "staples_wave1"):
        assert src in FORBIDDEN
        try:
            plan_sources([src])
        except ValueError as exc:
            assert src in str(exc)
        else:
            raise AssertionError(f"{src} should be refused")


def test_seed_prod_does_not_read_staples_wave1():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "seed_prod.py").read_text(
        encoding="utf-8"
    )
    assert "review_india.csv" not in src
    assert "batch_001_owner_accept.csv" not in src
    plan = plan_sources([])
    for item in plan:
        path = Path(item["path"]).resolve()
        staples = (_REPO / "data" / "staples_wave1").resolve()
        assert staples not in path.parents and path != staples, path
