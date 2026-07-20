"""Systemic commodity coverage + allergen identity derivation gates.

These tests encode the failure mode we hit in production reviews:
staging/layer1 dumps existed, but chat still returned Depends / missed
allergen Avoid because short names and identity flags never reached the
compliance seam. Gates must stay class-based (not one-ingredient patches).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolution_cache import clear as clear_resolution_cache
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores.local_ontology import reset_cache as reset_local_ontology

_REPO = Path(__file__).resolve().parents[3]
_EXPANDED = _REPO / "data" / "commodity_seed_lists" / "expanded_grocery.txt"


def _reload_indexes():
    clear_resolution_cache()
    reset_local_ontology()


@pytest.fixture(autouse=True)
def _fresh_indexes():
    _reload_indexes()
    yield
    _reload_indexes()


def test_fish_species_implies_fish_source():
    flags = derive_identity_flags("bass", {"animal_origin": True}, animal_species="fish")
    assert flags["fish_source"] is True


def test_peanut_name_implies_peanut_source():
    assert derive_identity_flags("peanut oil", {})["peanut_source"] is True
    assert derive_identity_flags("peanuts", {})["peanut_source"] is True


def test_water_chestnut_is_not_tree_nut():
    flags = derive_identity_flags("water chestnuts", {"tree_nut_source": False})
    assert flags.get("tree_nut_source") is not True


def test_eggplant_is_not_egg_source():
    flags = derive_identity_flags("eggplant", {})
    assert flags.get("egg_source") is not True


def test_coconut_is_not_tree_nut_by_name():
    flags = derive_identity_flags("coconut oil", {})
    assert flags.get("tree_nut_source") is not True


def test_almond_is_tree_nut():
    assert derive_identity_flags("almond", {})["tree_nut_source"] is True


def test_seam_derives_fish_source_for_species_only_row():
    """Under-flagged ontology rows with animal_species=fish must Avoid on fish allergy."""
    from types import SimpleNamespace

    resolved = SimpleNamespace(
        trusted=True,
        group=SimpleNamespace(
            canonical_name="bass",
            animal_origin=True,
            animal_species="fish",
            fish_source=False,  # under-flagged
            plant_origin=False,
            knowledge_state="AUTO_CLASSIFIED",
        ),
    )
    # GroupRow path uses vars(group)
    inp = to_compliance_input(resolved)
    assert inp.flags.get("fish_source") is True


@pytest.mark.skipif(not _EXPANDED.exists(), reason="expanded grocery seed missing")
def test_expanded_grocery_list_fully_resolves_trusted():
    items = [x.strip() for x in _EXPANDED.read_text(encoding="utf-8").split(",") if x.strip()]
    assert len(items) >= 400
    misses = []
    for raw in items:
        r = resolve(raw, None)
        if r.status != "resolved" or not r.trusted:
            misses.append((raw, r.resolution_layer, r.status, r.trusted))
    assert misses == [], f"{len(misses)} unresolved/untrusted e.g. {misses[:20]}"


@pytest.mark.skipif(not _EXPANDED.exists(), reason="expanded grocery seed missing")
def test_expanded_list_fish_names_carry_fish_source_via_seam():
    fish = [
        "Bass", "Carp", "Cod", "Flounder", "Haddock", "Halibut", "Herring",
        "Mackerel", "Salmon", "Sardines", "Snapper", "Sole", "Tilapia", "Trout",
    ]
    for name in fish:
        r = resolve(name, None)
        assert r.status == "resolved" and r.trusted, name
        inp = to_compliance_input(r, query_atom=name)
        assert inp.flags.get("fish_source") is True, f"{name} missing fish_source: {inp.flags}"


@pytest.mark.skipif(not _EXPANDED.exists(), reason="expanded grocery seed missing")
def test_expanded_list_peanut_names_carry_peanut_source_via_seam():
    for name in ("Peanuts", "Peanut oil"):
        r = resolve(name, None)
        assert r.status == "resolved" and r.trusted, name
        inp = to_compliance_input(r, query_atom=name)
        assert inp.flags.get("peanut_source") is True, name
