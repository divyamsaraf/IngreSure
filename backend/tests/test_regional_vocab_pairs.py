"""UK/AU/NZ/IN vs US pairs, US colour -> E-number, corn disambiguation seed."""
from __future__ import annotations

import json
from pathlib import Path

from core.external_apis.regional_names import resolve_static_regional_canonical
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.validate import validate_rows
from core.knowledge.ike2.variant_aliases import lookup_variant_alias, reset_variant_alias_cache
from core.normalization.normalizer import normalize_ingredient_key

_REPO = Path(__file__).resolve().parents[2]
_PAIRS = _REPO / "data" / "lexicon" / "regional_en_pairs.json"
_COLOURS = _REPO / "data" / "lexicon" / "us_colour_to_e_number.json"
_DISAMBIG = _REPO / "data" / "ike2_alias_disambiguation.json"

REGIONS = frozenset({"UK", "AU", "NZ", "IN", "US"})
HIGH_CONFIDENCE = (
    ("aubergine", "eggplant"),
    ("courgette", "zucchini"),
    ("capsicum", "bell pepper"),
    ("brinjal", "eggplant"),
    ("bhindi", "okra"),
    ("kumara", "sweet potato"),
    ("cornflour", "cornstarch"),
    ("icing sugar", "powdered sugar"),
    ("caster sugar", "superfine sugar"),
    ("beetroot", "beet"),
)


def test_one_hundred_regional_pairs():
    data = json.loads(_PAIRS.read_text(encoding="utf-8"))
    pairs = data["pairs"]
    assert len(pairs) >= 100
    seen = set()
    for row in pairs:
        assert row["regional"]
        assert row["us"]
        assert set(row["regions"]) <= REGIONS
        assert set(row["regions"]) & {"UK", "AU", "NZ", "IN"}
        key = (row["regional"].lower(), row["us"].lower())
        assert key not in seen, key
        seen.add(key)


def test_high_confidence_pairs_remap():
    for regional, us in HIGH_CONFIDENCE:
        got = resolve_static_regional_canonical(regional)
        assert got is not None, regional
        assert normalize_ingredient_key(got) == normalize_ingredient_key(us), (
            regional,
            got,
            us,
        )


def test_us_colour_names_map_to_e_numbers():
    reset_variant_alias_cache()
    data = json.loads(_COLOURS.read_text(encoding="utf-8"))
    mappings = data["mappings"]
    assert len(mappings) >= 12
    for row in mappings:
        assert row["us_name"]
        assert row["e_number"].upper().startswith("E")
        assert row["canonical_name"]
        alias = lookup_variant_alias(row["us_name"])
        assert alias, row["us_name"]
        target = normalize_ingredient_key(alias)
        allowed = {
            normalize_ingredient_key(row["e_number"]),
            normalize_ingredient_key(row["canonical_name"]),
        }
        assert target in allowed, (row["us_name"], alias)


def test_corn_disambiguation_seed_is_data_only():
    data = json.loads(_DISAMBIG.read_text(encoding="utf-8"))
    assert data["table"] == "ike2_alias_disambiguation"
    rows = [r for r in data["entries"] if r["normalized_alias"] == "corn"]
    regions = {r["context_region"] for r in rows}
    assert {"US", "AU", "NZ", "IN", "UK"} <= regions
    for row in rows:
        assert row["canonical_name"]
        assert row["context_region"]
    us = next(r for r in rows if r["context_region"] == "US")
    assert normalize_ingredient_key(us["canonical_name"]) in {
        "corn",
        "maize",
        "sweetcorn",
    }


def test_colour_and_pair_rows_true_only_through_adapt():
    """Reviewed-path gate: asserted flags stay true-only after adapt."""
    raw = {f: False for f in BOOL_FLAGS}
    raw.update(
        {
            "canonical_name": "tartrazine",
            "plant_origin": True,
            "synthetic": True,
            "asserted_flags": ["plant_origin", "synthetic"],
            "aliases": ["yellow 5", "fd&c yellow no. 5"],
        }
    )
    row, _ = map_record(raw, "ontology", "AUTO_CLASSIFIED")
    assert all(row.get(f) for f in row.get("asserted_flags") or [])
    ok, rejects = validate_rows([row])
    assert rejects == []
    assert ok
