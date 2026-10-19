"""Item 2 Prompt 2: propagate_process_flags pure helper."""
from core.knowledge.ike2.process_flags import PROCESS_FLAG_SET, propagate_process_flags


def test_process_flag_set_is_fungal_and_fermented_only():
    assert PROCESS_FLAG_SET == frozenset({"fungal", "fermented"})


def test_fungal_parent_ors_onto_plain_soy_member():
    parent = {"fungal": True, "soy_source": True}
    member = {"plant_origin": True, "soy_source": True}
    out = propagate_process_flags(parent, member)
    assert out["fungal"] is True
    assert out["soy_source"] is True
    assert out["plant_origin"] is True


def test_fermented_parent_preserved_on_member():
    parent = {"fermented": True}
    member = {"plant_origin": True}
    out = propagate_process_flags(parent, member)
    assert out["fermented"] is True
    assert out.get("fungal") is not True


def test_never_clears_member_positives():
    parent = {"fungal": False, "fermented": False}
    member = {"fungal": True, "fermented": True, "plant_origin": True}
    out = propagate_process_flags(parent, member)
    assert out["fungal"] is True
    assert out["fermented"] is True


def test_does_not_copy_dairy_source_from_parent():
    parent = {"fungal": True, "dairy_source": True, "animal_origin": True}
    member = {"plant_origin": True}
    out = propagate_process_flags(parent, member)
    assert out["fungal"] is True
    assert "dairy_source" not in out or out.get("dairy_source") is not True
    assert out.get("animal_origin") is not True


def test_both_process_flags_or_from_parent():
    parent = {"fungal": True, "fermented": True}
    member = {}
    out = propagate_process_flags(parent, member)
    assert out == {"fungal": True, "fermented": True}


def test_empty_parent_leaves_member_unchanged():
    member = {"plant_origin": True, "soy_source": True}
    assert propagate_process_flags({}, member) == member
