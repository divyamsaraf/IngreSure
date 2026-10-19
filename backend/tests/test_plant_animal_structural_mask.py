"""Structural plant+animal false-friend masks (shared lexicon)."""
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.parsing.hazard_lexicon import hazard_hits_in_text


_GOLDENS_NO_DAIRY = (
    "beurre de cacahuète",
    "beurre de karité",
    "crème de coco",
    "Haferdrink",
    "Sojajoghurt",
    "cashew cheese",
    "almond milk",
    "peanut butter",
    "cocoa butter",
    "tofu yogurt",
)


def test_structural_plant_animal_masks_dairy():
    for text in _GOLDENS_NO_DAIRY:
        assert "dairy" not in hazard_hits_in_text(text), text
        assert not derive_identity_flags(text).get("dairy_source"), text


def test_vegan_egg_masks_egg():
    assert "egg" not in hazard_hits_in_text("vegan egg")
    assert not derive_identity_flags("vegan egg").get("egg_source")


def test_plant_based_chicken_does_not_fire_egg_or_dairy():
    hits = hazard_hits_in_text("plant-based chicken")
    assert "egg" not in hits and "dairy" not in hits


def test_independent_animal_token_still_fires():
    """Span mask only — bare milk next to almond milk still counts."""
    assert "dairy" in hazard_hits_in_text("almond milk, milk")
    assert "dairy" in hazard_hits_in_text("beurre de cacao, beurre")


def test_non_dairy_claim_is_negation_not_safe_signal():
    """non-dairy / dairy-free are claims (no lexicon dairy hit)."""
    assert "dairy" not in hazard_hits_in_text("non-dairy creamer")
    assert "dairy" not in hazard_hits_in_text("dairy-free cheese")
    # Caseinate in a non-dairy creamer still fires when present.
    assert "dairy" in hazard_hits_in_text("non-dairy creamer, sodium caseinate")


def test_real_dairy_and_peanut_butter_peanut_still_hit():
    assert "dairy" in hazard_hits_in_text("butter")
    assert "peanut" in hazard_hits_in_text("beurre de cacahuète")
    assert "peanut" in hazard_hits_in_text("peanut butter")
