from scripts.seed_prod import ALLOWED_L1, FORBIDDEN, plan_sources


def test_default_plan_is_ontology_plus_allowlisted_l1():
    plan = plan_sources([])
    names = [p["source"] for p in plan]
    assert names[0] == "ontology"
    assert set(names[1:]) <= ALLOWED_L1
    assert "produce_catalog" in names
    assert "animal_catalog" in names
    assert "infoods" in names


def test_forbidden_sources_rejected():
    for src in ("unknown_queue", "shadow", "usda", "fssai"):
        assert src in FORBIDDEN
        try:
            plan_sources([src])
        except ValueError as exc:
            assert src in str(exc)
        else:
            raise AssertionError(f"{src} should be refused")
