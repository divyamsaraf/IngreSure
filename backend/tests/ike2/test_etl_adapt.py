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


def test_provenance_source_set_from_canonical():
    row, _ = map_record(_raw(), "usda", "AUTO_CLASSIFIED")
    assert row["source"] == "usda"
    assert row["classification_method"] == "bulk:usda"


def test_non_enumber_dump_locked_passes_to_validate_for_hard_reject():
    """adapt keeps declared LOCKED so validate can quarantine — no silent downgrade."""
    from core.knowledge.ike2.etl.validate import validate_rows

    row, _ = map_record(
        _raw(knowledge_state="LOCKED", primary_source_url="https://example.com"),
        "usda",
        "AUTO_CLASSIFIED",
    )
    assert row["knowledge_state"] == "LOCKED"
    ok, rejects = validate_rows([row])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "bulk_locked_verified_requires_e_number_catalog"


def test_asserted_flags_only_keys_present_in_raw():
    row, _ = map_record(_raw(), "usda", "AUTO_CLASSIFIED")
    # _raw sets plant_origin and gluten_source; omitted flags stay False and unasserted.
    assert "plant_origin" in row["asserted_flags"]
    assert "gluten_source" in row["asserted_flags"]
    assert "synthetic" not in row["asserted_flags"]
    assert row["synthetic"] is False


def test_sparse_false_keys_are_not_asserted():
    """Bulk adapters assert trues only; sparse falses need curated asserted_flags."""
    false_keys = [
        "synthetic",
        "animal_origin",
        "dairy_source",
        "egg_source",
        "fish_source",
        "shellfish_source",
        "gluten_source",
        "soy_source",
        "peanut_source",
        "tree_nut_source",
        "fungal",
        "insect_derived",
    ]
    assert 4 <= len(false_keys) <= 12
    raw = {k: False for k in false_keys}
    raw.update({"canonical_name": "plain rice", "plant_origin": True, "aliases": []})
    row, _ = map_record(raw, "ifct", "AUTO_CLASSIFIED")
    false_asserted = [f for f in row["asserted_flags"] if not row.get(f)]
    assert false_asserted == []
    assert "plant_origin" in row["asserted_flags"]
    for k in false_keys:
        assert k not in row["asserted_flags"], k
        assert row[k] is False


def test_asserted_flags_respects_curated_list_when_present():
    """Ontology-style dumps ship every bool key; asserted_flags is the decision list."""
    row, _ = map_record(
        _raw(
            plant_origin=True,
            gluten_source=True,
            synthetic=False,
            dairy_source=False,
            asserted_flags=["plant_origin", "gluten_source", "dairy_source"],
        ),
        "ontology",
        "AUTO_CLASSIFIED",
    )
    assert "plant_origin" in row["asserted_flags"]
    assert "gluten_source" in row["asserted_flags"]
    assert "dairy_source" in row["asserted_flags"]  # deliberate false-friend
    assert "synthetic" not in row["asserted_flags"]


def test_asserted_flags_include_nut_derive_and_forced_animal():
    row, _ = map_record(
        _raw(nut_source="peanut", insect_derived=True, plant_origin=False, gluten_source=False),
        "usda",
        "AUTO_CLASSIFIED",
    )
    assert row["peanut_source"] is True
    assert "peanut_source" in row["asserted_flags"]
    assert row["animal_origin"] is True
    assert "animal_origin" in row["asserted_flags"]
    assert "insect_derived" in row["asserted_flags"]
