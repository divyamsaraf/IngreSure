"""Sulfite stems in derive_identity_flags (Item 7 / 2026-10-07)."""
from core.knowledge.ike2.flag_derive import derive_identity_flags


def test_sodium_sulfite_derives_sulphite_source():
    assert derive_identity_flags("sodium sulfite", {})["sulphite_source"] is True
    assert derive_identity_flags("sodium sulphite", {})["sulphite_source"] is True


def test_metabisulphite_british_spelling_derives():
    assert derive_identity_flags("sodium metabisulphite", {})["sulphite_source"] is True


def test_sulfur_dioxide_and_e_codes_derive():
    assert derive_identity_flags("sulfur dioxide", {})["sulphite_source"] is True
    assert derive_identity_flags("e221", {})["sulphite_source"] is True


def test_sulfate_and_acesulfame_do_not_derive_sulphite():
    assert derive_identity_flags("sodium sulphate", {}).get("sulphite_source") is not True
    assert derive_identity_flags("calcium sulfate", {}).get("sulphite_source") is not True
    assert derive_identity_flags("acesulfame k", {}).get("sulphite_source") is not True


def test_sulfured_fruit_treatment_derives_sulphite():
    for name in (
        "sulfured",
        "sulphured",
        "sulfited",
        "sulphited",
        "apples dried sulfured uncooked",
        "apricots dried sulphured uncooked",
        "dried sulfured fruit",
    ):
        assert derive_identity_flags(name, {})["sulphite_source"] is True, name
    # sulfate esters / salts stay out
    assert derive_identity_flags("sulfated ash", {}).get("sulphite_source") is not True
    assert derive_identity_flags("sodium sulphate", {}).get("sulphite_source") is not True
