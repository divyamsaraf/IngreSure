from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent


def test_sulphite_flag_is_allergen_adjacent():
    assert is_allergen_adjacent({"plant_origin": True, "sulphite_source": True}) is True


def test_mollusc_species_is_allergen_adjacent():
    assert is_allergen_adjacent({"animal_origin": True, "animal_species": "mollusk"}) is True
    assert is_allergen_adjacent({"animal_origin": True, "animal_species": "mollusc"}) is True


def test_plain_broccoli_not_allergen_adjacent():
    assert is_allergen_adjacent({"plant_origin": True, "animal_origin": False}) is False
