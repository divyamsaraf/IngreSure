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


def test_chat_short_names_ragi_flax_paneer_resolve():
    """Regression: regional/spacing variants must not fall through to Depends."""
    from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache

    reset_variant_alias_cache()
    cases = {
        "ragi": "finger millet",
        "flax seeds": "flaxseeds",
        "paneer": "paneer",
    }
    for raw, canon in cases.items():
        r = resolve(raw, None)
        assert r.status == "resolved" and r.trusted, raw
        assert r.group.canonical_name == canon, (raw, r.group.canonical_name)
        inp = to_compliance_input(r, query_atom=raw)
        if canon == "paneer":
            assert inp.flags.get("dairy_source") is True, raw


def test_affogato_is_compound_never_firm_safe_or_dairy_invented():
    """Affogato composition unknown (dairy and/or egg gelato possible) — WARN only."""
    from types import SimpleNamespace

    from core.knowledge.ike2 import compliance as compliance_module
    from core.knowledge.ike2 import rules as rules_module
    from core.knowledge.ike2.verdict import Verdict, to_external

    r = resolve("affogato", None)
    assert r.status == "resolved" and r.trusted
    assert r.resolution_layer == "L1_truth_anchor"
    inp = to_compliance_input(r, query_atom="affogato")
    assert inp.verdict_cap == "WARN"
    assert inp.flags.get("dairy_source") is not True
    assert inp.flags.get("egg_source") is not True
    rules = rules_module.seeded_rules()
    for restriction in ("vegan", "egg_allergy", "milk_allergy", "dairy_free"):
        if restriction not in rules_module.SUPPORTED_RESTRICTIONS:
            continue
        profile = SimpleNamespace(restrictions={restriction: "medical"})
        result = compliance_module.evaluate([inp], profile, rules)
        assert result.verdict != Verdict.SAFE, restriction
        assert result.verdict != Verdict.FAIL, restriction  # no invented Avoid
        assert to_external(result.verdict) == "UNCERTAIN", restriction


def test_compound_dishes_not_firm_plant_safe():
    """Souffle / ice cream sandwich must not be firm plant Safe (egg/dairy possible)."""
    for raw in ("spinach souffle", "ice cream sandwich", "souffle", "veggie burger"):
        r = resolve(raw, None)
        assert r.status == "resolved", raw
        inp = to_compliance_input(r, query_atom=raw)
        assert inp.verdict_cap == "WARN" or not r.trusted or inp.flags.get("plant_origin") is not True or r.resolution_layer == "L1_truth_anchor", raw
        if r.resolution_layer == "L1_truth_anchor":
            assert inp.verdict_cap == "WARN", raw


def test_paneer_does_not_steal_cottage_cheese():
    r_paneer = resolve("paneer", None)
    r_cottage = resolve("cottage cheese", None)
    assert r_paneer.group.canonical_name == "paneer"
    assert r_cottage.group.canonical_name == "cottage cheese"
    aliases = [a.lower() for a in (getattr(r_paneer.group, "aliases", None) or [])]
    # group may be TruthAnchorFact without aliases; check ontology via resolve identity only
    assert r_cottage.group.canonical_name != "paneer"


def test_nin_canonicals_resolve_trusted():
    nin_path = _REPO / "data" / "layer1_nin.json"
    if not nin_path.exists():
        pytest.skip("layer1_nin missing")
    import json

    rows = json.loads(nin_path.read_text(encoding="utf-8"))
    misses = []
    for raw in rows:
        name = (raw.get("canonical_name") or "").strip()
        if not name:
            continue
        r = resolve(name, None)
        if r.status != "resolved" or not r.trusted:
            misses.append(name)
    assert misses == [], f"NIN unresolved: {misses[:20]}"


def test_static_regional_keys_resolve_trusted():
    from core.external_apis.regional_names import _load_static, _static_only_regional
    from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache

    reset_variant_alias_cache()
    _load_static()
    misses = []
    for key in sorted(_static_only_regional):
        raw = key.replace("_", " ")
        r = resolve(raw, None)
        if r.status != "resolved" or not r.trusted:
            misses.append(raw)
    assert misses == [], f"regional unresolved: {misses[:20]}"


def test_atta_carries_gluten_via_seam():
    r = resolve("atta", None)
    assert r.status == "resolved" and r.trusted
    inp = to_compliance_input(r, query_atom="atta")
    assert inp.flags.get("gluten_source") is True


def test_bajra_and_poha_resolve():
    for raw in ("bajra", "poha", "hing", "makhana", "jaggery"):
        r = resolve(raw, None)
        assert r.status == "resolved" and r.trusted, raw


def test_dump_style_short_names_resolve_via_live_ontology():
    """Regression class: USDA-style rows must be reachable as chat short names."""
    from core.knowledge.ike2.commodity_head import simple_commodity_head
    from core.knowledge.ike2.etl.load_ontology import load_ontology_records
    from core.normalization.normalizer import normalize_ingredient_key

    samples: list[tuple[str, str]] = []
    for raw in load_ontology_records():
        canon = raw.get("canonical_name") or ""
        head = simple_commodity_head(canon)
        if not head:
            continue
        if head == normalize_ingredient_key(canon):
            continue
        samples.append((head, canon))
        if len(samples) >= 40:
            break
    if len(samples) < 5:
        for probe in ("broccoli, raw", "spinach, raw", "kale, raw", "carrot, raw", "onion, raw"):
            h = simple_commodity_head(probe)
            if h:
                samples.append((h, probe))
    assert len(samples) >= 5, "expected dump-style heads to probe"
    misses = []
    for head, canon in samples:
        r = resolve(head, None)
        if r.status != "resolved" or not r.trusted:
            misses.append((head, canon, r.status))
    assert misses == [], f"short-name misses: {misses[:15]}"