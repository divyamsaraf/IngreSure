"""Frozen reviewed clears: dump may only assert-clear names on the committed list."""
import json
from pathlib import Path

from core.external_apis.usda_fdc import REVIEWED_ASSERTED_CLEARS, asserted_clear_allowed
from core.normalization.normalizer import normalize_ingredient_key
from scripts.transform_usda_fdc_bulk import _food_to_layer1_row

_REPO = Path(__file__).resolve().parents[3]
_CLEARS = _REPO / "data" / "usda_reviewed_asserted_clears.json"
_DUMP = _REPO / "data" / "layer1_usda_fdc.json"


def test_reviewed_clears_file_is_marked_frozen():
    data = json.loads(_CLEARS.read_text(encoding="utf-8"))
    assert data.get("frozen") is True
    assert "FROZEN" in (data.get("provenance") or "").upper() or data.get("frozen")


def test_dump_asserted_clears_subset_of_reviewed_list():
    dump = json.loads(_DUMP.read_text(encoding="utf-8"))
    allowed = REVIEWED_ASSERTED_CLEARS
    extras = []
    for r in dump:
        af = r.get("asserted_flags") or []
        for flag in af:
            if r.get(flag):
                continue
            key = (normalize_ingredient_key(r["canonical_name"]), flag)
            if key not in allowed:
                extras.append(key)
    assert extras == [], f"dump clears not on frozen list: {extras[:20]}"


def test_transform_refuses_clear_not_on_list():
    # Cheese sauce is processed-form — must not get asserted egg clear.
    assert asserted_clear_allowed("Cheese sauce, prepared from recipe", "egg_source") is False
    row = _food_to_layer1_row(
        {
            "description": "Cheese sauce, prepared from recipe",
            "foodCategory": {"description": "Dairy and Egg Products"},
        },
        strict=False,
    )
    assert "egg_source" not in (row.get("asserted_flags") or [])
