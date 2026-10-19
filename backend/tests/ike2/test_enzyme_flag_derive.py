"""Item 3.1 Prompt 3: flag_derive + truth anchors for animal enzymes."""
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.truth_anchor import lookup as truth_lookup


def test_rennet_derives_enzyme_animal_and_animal_origin():
    flags = derive_identity_flags("rennet", {})
    assert flags.get("enzyme_animal_source") is True
    assert flags.get("animal_origin") is True


def test_animal_rennet_phrase():
    flags = derive_identity_flags("animal rennet", {})
    assert flags.get("enzyme_animal_source") is True
    assert flags.get("animal_origin") is True


def test_pepsin_derives_enzyme_animal():
    flags = derive_identity_flags("pepsin", {})
    assert flags.get("enzyme_animal_source") is True


def test_microbial_rennet_not_animal_enzyme():
    flags = derive_identity_flags("microbial rennet", {})
    assert flags.get("enzyme_animal_source") is not True


def test_bare_enzymes_do_not_derive_animal_enzyme():
    flags = derive_identity_flags("enzymes", {})
    assert flags.get("enzyme_animal_source") is not True
    flags2 = derive_identity_flags("enzyme", {})
    assert flags2.get("enzyme_animal_source") is not True


def test_truth_anchor_rennet_has_enzyme_animal_source():
    fact = truth_lookup("rennet")
    assert fact is not None
    assert fact.flags.get("animal_origin") is True
    assert fact.flags.get("enzyme_animal_source") is True


def test_truth_anchor_pepsin_has_enzyme_animal_source():
    fact = truth_lookup("pepsin")
    assert fact is not None
    assert fact.flags.get("enzyme_animal_source") is True


def test_truth_anchor_bare_enzymes_still_compound_warn_only():
    fact = truth_lookup("enzymes")
    assert fact is not None
    assert fact.flags.get("verdict_cap") == "WARN"
    assert fact.flags.get("enzyme_animal_source") is not True
