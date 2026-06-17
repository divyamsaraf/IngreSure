from core.knowledge.ike2.truth_anchor import lookup


def test_gelatin_is_animal_and_locked():
    fact = lookup("gelatin")
    assert fact is not None
    assert fact.flags["animal_origin"] is True
    assert fact.knowledge_state == "LOCKED"


def test_carmine_e120_is_insect():
    for key in ("carmine", "e120", "cochineal"):
        fact = lookup(key)
        assert fact is not None, key
        assert fact.flags["insect_derived"] is True


def test_unknown_key_returns_none():
    assert lookup("totally_unknown_thing_xyz") is None
