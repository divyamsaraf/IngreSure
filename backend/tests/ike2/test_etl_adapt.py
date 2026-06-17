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


def test_nut_source_is_dropped_as_a_column():
    row, _ = map_record(_raw(nut_source="peanut"), "usda", "AUTO_CLASSIFIED")
    assert "nut_source" not in row


def test_peanut_string_sets_peanut_flag_not_tree_nut():
    # nut_source is free-text (e.g. "peanut butter, creamy"); the old code folded
    # any truthy value into tree_nut_source, hiding peanut from peanut-allergic users.
    row, _ = map_record(_raw(nut_source="peanut butter, creamy"), "usda", "AUTO_CLASSIFIED")
    assert row["peanut_source"] is True
    assert row["tree_nut_source"] is False


def test_tree_nut_strings_set_tree_nut_flag():
    for text in ("almond paste", "roasted hazelnuts", "cashew nut oil", "tree_nut"):
        row, _ = map_record(_raw(nut_source=text), "usda", "AUTO_CLASSIFIED")
        assert row["tree_nut_source"] is True, text
        assert row["peanut_source"] is False, text


def test_coconut_maps_to_neither():
    # Coconut allergy is medically distinct from tree-nut allergy and there is no
    # coconut_source flag/rule, so "coconut" is a RECOGNIZED value mapped to neither
    # (faithful to restrictions.json, which matches neither peanut nor tree_nut).
    # It must NOT hit the unrecognized -> both-True fail-closed fallback.
    row, _ = map_record(_raw(nut_source="coconut"), "usda", "AUTO_CLASSIFIED")
    assert row["peanut_source"] is False
    assert row["tree_nut_source"] is False


def test_mixed_peanut_and_tree_nut_string_sets_both():
    row, _ = map_record(_raw(nut_source="sauce, peanut, made from almond"), "usda", "AUTO_CLASSIFIED")
    assert row["peanut_source"] is True
    assert row["tree_nut_source"] is True


def test_ambiguous_or_legacy_truthy_nut_overflags_both():
    # unrecognized but truthy -> fail closed (over-flag is a false-Avoid, acceptable;
    # under-flagging a nut is not).
    for val in (True, "nut", "mixed unidentified nut blend"):
        row, _ = map_record(_raw(nut_source=val), "usda", "AUTO_CLASSIFIED")
        assert row["peanut_source"] is True, val
        assert row["tree_nut_source"] is True, val


def test_alcohol_content_sets_ingredient_role():
    row, _ = map_record(_raw(alcohol_content=40.0), "usda", "AUTO_CLASSIFIED")
    assert row["alcohol_role"] == "ingredient"


def test_fermented_without_explicit_alcohol_sets_trace_role():
    row, _ = map_record(_raw(fermented=True), "usda", "AUTO_CLASSIFIED")
    assert row["alcohol_role"] == "fermentation_trace"


def test_no_alcohol_signal_is_none_role():
    row, _ = map_record(_raw(), "usda", "AUTO_CLASSIFIED")
    assert row["alcohol_role"] == "none"


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
