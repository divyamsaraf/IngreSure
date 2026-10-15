"""Item 11 INFOODS AnFooD2.0: head-commodity canonical form (unit tests first)."""
from core.knowledge.ike2.etl.adapters.infoods_anfood import (
    flags_for_sheet,
    head_commodity,
    merge_anfood_records,
    normalize_anfood_row,
)


def test_head_commodity_strips_processing_not_species():
    assert head_commodity("African catfish farmed skinless boneless fillet boiled") == (
        "african catfish"
    )
    assert head_commodity("Spinach, raw") == "spinach"
    assert head_commodity("Amaranth blanched") == "amaranth"


def test_canonical_is_head_full_string_and_sci_are_aliases():
    row = normalize_anfood_row(
        sheet="09 Fish & Shellfish",
        english="African catfish farmed skinless boneless fillet boiled",
        local="mlamba",
        scientific="Clarias gariepinus",
        subgroup="Finfish",
        country="Malawi",
        food_id="F001",
    )
    assert row is not None
    assert row["canonical_name"] == "african catfish"
    aliases = {a.lower() for a in row["aliases"]}
    assert "african catfish farmed skinless boneless fillet boiled" in aliases
    assert "clarias gariepinus" in aliases
    assert "mlamba" in aliases
    assert row["animal_origin"] is True
    assert row["fish_source"] is True
    assert row.get("plant_origin") is not True
    assert "infoods_anfood_inferred" in row["uncertainty_flags"]
    assert row["source"] == "infoods"


def test_shellfish_from_mollusc_subgroup():
    row = normalize_anfood_row(
        sheet="09 Fish & Shellfish",
        english="Abalone edible flesh raw",
        local="",
        scientific="Haliotis midae",
        subgroup="Molluscs",
        country="",
        food_id="",
    )
    assert row["shellfish_source"] is True
    assert row.get("fish_source") is not True
    assert row["animal_origin"] is True


def test_shellfish_from_name_when_subgroup_misses_scallop():
    """american sea scallop was fish_only because subgroup was not molluscs."""
    row = normalize_anfood_row(
        sheet="09 Fish & Shellfish",
        english="American sea scallop raw",
        local="",
        scientific="",
        subgroup="Finfish",
        country="USA",
        food_id="",
    )
    assert row["shellfish_source"] is True
    assert row.get("fish_source") is not True


def test_plant_sheet_flags():
    flags = flags_for_sheet("03 Legumes", subgroup=None)
    assert flags["plant_origin"] is True
    assert flags.get("animal_origin") is not True


def test_merge_dedupes_by_canonical_and_unions_aliases():
    a = normalize_anfood_row(
        sheet="05 Vegetables",
        english="Spinach raw",
        local="palak",
        scientific="Spinacia oleracea",
        subgroup=None,
        country="India",
        food_id="V1",
    )
    b = normalize_anfood_row(
        sheet="05 Vegetables",
        english="Spinach boiled",
        local="",
        scientific="Spinacia oleracea",
        subgroup=None,
        country="India",
        food_id="V2",
    )
    merged = merge_anfood_records([a, b])
    assert len(merged) == 1
    assert merged[0]["canonical_name"] == "spinach"
    aliases_l = {x.lower() for x in merged[0]["aliases"]}
    assert "spinach raw" in aliases_l
    assert "spinach boiled" in aliases_l
    assert "palak" in aliases_l
