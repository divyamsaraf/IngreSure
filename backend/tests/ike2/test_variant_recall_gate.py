"""Variant recall gate + synonymy-ladder contracts (design §9.3.1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge.ike2.commodity_head import facet_reduction_candidates, simple_commodity_head
from core.knowledge.ike2.miss_class import classify_miss_class
from core.knowledge.ike2.resolution_cache import clear
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.stores.local_ontology import reset_cache
from core.knowledge.ike2.variant_aliases import lookup_variant_alias, reset_variant_alias_cache
from core.normalization.normalizer import normalize_ingredient_key

_REPO = Path(__file__).resolve().parents[3]
_RECALL = _REPO / "data" / "commodity_seed_lists" / "variant_recall.txt"
_MIN_RECALL = 0.85


@pytest.fixture(autouse=True)
def _fresh():
    clear()
    reset_cache()
    reset_variant_alias_cache()
    yield
    clear()
    reset_cache()
    reset_variant_alias_cache()


def test_apostrophe_fold_bakers_yeast():
    assert normalize_ingredient_key("Baker's yeast") == normalize_ingredient_key("bakers yeast")
    r = resolve("Baker's yeast", None)
    assert r.status == "resolved" and r.trusted
    assert r.group.canonical_name == "yeast"


def test_variant_alias_longest_cut():
    assert lookup_variant_alias("beef brisket") == "beef"
    r = resolve("Beef brisket", None)
    assert r.status == "resolved" and r.trusted


def test_head_first_salt_and_color_rice():
    assert "himalayan salt" in facet_reduction_candidates("salt himalayan")
    assert "rice" in facet_reduction_candidates("white rice")
    assert resolve("salt himalayan", None).status == "resolved"
    assert resolve("white rice", None).status == "resolved"
    assert resolve("sugar brown", None).group.canonical_name == "brown sugar"


def test_animal_cut_aliases_avoid_hindu_veg():
    from types import SimpleNamespace
    from core.knowledge.ike2.compliance import Verdict, evaluate
    from core.knowledge.ike2.seam import to_compliance_input
    from core.knowledge.ike2.rules import seeded_rules

    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "preference"})
    for raw in (
        "smoked ham", "turkey ground", "sheep", "seafood", "tenderloin",
        "yolks", "snail", "worcestershire sauce",
    ):
        r = resolve(raw, None)
        assert r.status == "resolved", raw
        inp = to_compliance_input(r, query_atom=raw)
        result = evaluate([inp], profile, seeded_rules())
        assert result.verdict == Verdict.FAIL, (raw, result.verdict)


def test_geo_fish_alias():
    r = resolve("Atlantic salmon", None)
    assert r.status == "resolved" and r.trusted


def test_facet_leaves_when_parent_exists():
    cands = facet_reduction_candidates("basil leaves")
    assert "basil" in cands
    r = resolve("Basil leaves", None)
    assert r.status == "resolved" and r.trusted


def test_forbidden_juice_not_blind_stripped_to_unsafe():
    # juice is forbidden as a generic strip; apple puree is curated alias only.
    assert "apple" not in facet_reduction_candidates("mystery juice xyz")
    head = simple_commodity_head("mystery juice xyz")
    assert head is None or head != "mystery"


def test_peanut_butter_not_reduced_to_butter():
    assert lookup_variant_alias("peanut butter") in (None, "peanut butter")
    r = resolve("Peanut butter", None)
    assert r.status == "resolved"
    name = (r.group.canonical_name or "").lower()
    assert "peanut" in name
    assert name != "butter"


def test_water_chestnut_not_tree_nut_collision():
    r = resolve("Water chestnuts", None)
    assert r.status == "resolved" and r.trusted
    from core.knowledge.ike2.seam import to_compliance_input
    inp = to_compliance_input(r, query_atom="Water chestnuts")
    assert inp.flags.get("tree_nut_source") is not True


def test_unknown_still_fail_closed_with_miss_class():
    r = resolve("zzzx_totally_unknown_coverage_fixture", None)
    assert r.status == "uncertain"
    assert r.trusted is False
    assert r.miss_class  # tagged for offline promote


def test_classify_miss_class_shapes():
    assert classify_miss_class("Beef brisket").startswith("M2")
    assert classify_miss_class("Atlantic salmon").startswith("M3")
    assert classify_miss_class("Basil leaves").startswith("M4")
    assert classify_miss_class("Apple juice").startswith("M5")
    assert classify_miss_class("Bacon fat").startswith("M7")


@pytest.mark.skipif(not _RECALL.exists(), reason="variant_recall corpus missing")
def test_variant_recall_corpus_meets_floor():
    items = [
        x.strip()
        for x in _RECALL.read_text(encoding="utf-8").replace("\n", " ").split(",")
        if x.strip()
    ]
    assert len(items) >= 100
    misses = []
    for raw in items:
        r = resolve(raw, None)
        if r.status != "resolved" or not r.trusted:
            misses.append((raw, r.resolution_layer, r.miss_class))
    rate = 1.0 - (len(misses) / len(items))
    assert rate >= _MIN_RECALL, (
        f"variant recall {rate:.1%} < {_MIN_RECALL:.0%}; "
        f"misses={len(misses)} e.g. {misses[:25]}"
    )
