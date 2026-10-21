"""Regional allergen packs: every regulated allergen maps to a rule and derive tokens."""
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.rules import RULE_SEED, SUPPORTED_RESTRICTIONS

_REPO = Path(__file__).resolve().parents[2]
_REGIONS = _REPO / "data" / "regions"

REQUIRED_FILES = ("eu", "uk", "au", "nz", "ca", "us", "in", "ae")
FLAG_BY_ALLERGEN = {
    "celery": "celery_source",
    "gluten": "gluten_source",
    "crustacean": "shellfish_source",
    "egg": "egg_source",
    "fish": "fish_source",
    "lupin": "lupin_source",
    "dairy": "dairy_source",
    "mollusc": "shellfish_source",
    "mustard": "mustard_source",
    "tree_nut": "tree_nut_source",
    "peanut": "peanut_source",
    "sesame": "sesame_source",
    "soy": "soy_source",
    "sulphite": "sulphite_source",
}
RID_BY_ALLERGEN = {
    "celery": "celery_allergy",
    "gluten": "gluten_free",
    "crustacean": "shellfish_allergy",
    "egg": "egg_free",
    "fish": "fish_allergy",
    "lupin": "lupin_allergy",
    "dairy": "dairy_free",
    "mollusc": "shellfish_allergy",
    "mustard": "mustard_allergy",
    "tree_nut": "tree_nut_allergy",
    "peanut": "peanut_allergy",
    "sesame": "sesame_allergy",
    "soy": "soy_allergy",
    "sulphite": "sulfite_sensitive",
}
SEEDED_CATEGORIES = {row["category"] for row in RULE_SEED}


def _load(code: str) -> dict:
    return json.loads((_REGIONS / f"{code}.json").read_text(encoding="utf-8"))


def test_region_files_exist_with_sources():
    for code in REQUIRED_FILES:
        data = _load(code)
        assert data["region"] == code.upper() if code != "ae" else data["region"] == "AE"
        assert "allergens" in data
        assert "numbering" in data
        assert "emergency_numbers" in data
        assert data["sources"], code
        for src in data["sources"]:
            assert src["url"].startswith("http"), src
            assert src["retrieved"], src
        assert "verified" in data


def test_uae_stays_unverified():
    assert _load("ae")["verified"] is False


def test_every_regulated_allergen_maps_to_rule_and_derive():
    for code in REQUIRED_FILES:
        data = _load(code)
        for allergen in data["allergens"]:
            aid = allergen["id"]
            rid = allergen["restriction_id"]
            flag = allergen["flag"]
            token = allergen["derive_token"]
            assert rid == RID_BY_ALLERGEN[aid], (code, aid, rid)
            assert flag == FLAG_BY_ALLERGEN[aid], (code, aid, flag)
            assert rid in SUPPORTED_RESTRICTIONS
            assert rid in SEEDED_CATEGORIES
            assert derive_identity_flags(token).get(flag) is True, (code, aid, token, flag)


def test_eu_has_fourteen_and_au_includes_oats():
    eu_ids = {a["id"] for a in _load("eu")["allergens"]}
    assert len(_load("eu")["allergens"]) == 14
    assert eu_ids == set(RID_BY_ALLERGEN)
    au = _load("au")
    gluten = next(a for a in au["allergens"] if a["id"] == "gluten")
    cereals = {c.lower() for c in gluten.get("cereals") or []}
    assert "oats" in cereals
    assert any(a["id"] == "sesame" for a in au["allergens"])
    assert any(a["id"] == "lupin" for a in au["allergens"])
    assert any(a["id"] == "mollusc" for a in au["allergens"])
    assert any(a["id"] == "sulphite" for a in au["allergens"])
