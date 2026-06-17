from core.knowledge.ike2.etl.adapt import map_record


def _raw(**over):
    base = {
        "id": "pasta_x",
        "canonical_name": "Pasta From Wheat",
        "aliases": ["Pasta From Wheat", "wheat pasta"],
        "plant_origin": True,
        "gluten_source": True,
        "nut_source": None,
        "uncertainty_flags": [],
        "regions": ["Global"],
        "derived_from": [],
        "contains": [],
        "_source": "open_food_facts",
        "_fdc_id": 1,
    }
    base.update(over)
    return base


def test_canonical_name_and_aliases_are_normalized_and_deduped():
    row, aliases = map_record(_raw(), "openfoodfacts", "DISCOVERED")
    assert row["canonical_name"] == "pasta from wheat"
    # canonical is included once; duplicate of canonical is collapsed
    norms = [a for a, _ in aliases]
    assert "pasta from wheat" in norms
    assert "wheat pasta" in norms
    assert len(norms) == len(set(norms))


def test_global_region_maps_to_none():
    _, aliases = map_record(_raw(), "openfoodfacts", "DISCOVERED")
    assert all(region is None for _, region in aliases)


def test_legacy_nut_source_maps_to_tree_nut_and_is_dropped():
    row, _ = map_record(_raw(nut_source=True), "usda", "AUTO_CLASSIFIED")
    assert row["tree_nut_source"] is True
    assert "nut_source" not in row


def test_only_ike2_columns_are_emitted():
    row, _ = map_record(_raw(), "openfoodfacts", "DISCOVERED")
    for junk in ("id", "derived_from", "contains", "_source", "_fdc_id", "aliases", "regions"):
        assert junk not in row
    assert row["knowledge_state"] == "DISCOVERED"
    assert row["plant_origin"] is True
    assert row["gluten_source"] is True
    # untouched flags default to False, not missing
    assert row["animal_origin"] is False


def test_uncertainty_flags_carried_through():
    row, _ = map_record(_raw(uncertainty_flags=["requires_classification"]),
                        "wikidata", "DISCOVERED")
    assert row["uncertainty_flags"] == ["requires_classification"]
