import json
from pathlib import Path

import pytest

from core.intent_detector import detect_intent
from core.knowledge.ike2 import resolution_cache
from tests.ike2.audit_matrix_helpers import run_audit_case

ROWS = [
    json.loads(line)
    for line in Path(__file__).with_name("golden").joinpath("audit_matrix.jsonl").read_text().splitlines()
    if line.strip() and not line.strip().startswith("#")
]

TIER1_ELIGIBLE_CLUSTERS = frozenset(
    {
        "sugar_family",
        "staples",
        "meats_on_veg",
        "egg_hnv",
        "warn_compounds",
        "jain_roots",
        "pescatarian_meats",
        "species_unknown",
        "gelatin_diet_vs_allergen",
        "breakdown_overwrite",
    }
)
TIER1_ELIGIBLE_ROWS = [row for row in ROWS if row["cluster"] in TIER1_ELIGIBLE_CLUSTERS]


def _assert_audit_matrix_row(row, result):
    name = row["input"].lower()
    bucket = result["bucket_by_name"].get(name) or next(
        (b for k, b in result["bucket_by_name"].items() if name in k or k in name), None
    )
    assert bucket == row["expect_bucket"], result
    cat = result["reason_category_by_name"].get(name) or result["reason_category_by_name"].get(
        next((k for k in result["reason_category_by_name"] if name in k or k in name), ""), None
    )
    assert cat == row["expect_reason_category"]
    if row.get("expect_attribution") == "diet":
        assert "allergen" not in (result["explanation"] or "").lower()
    blanket = "may conflict with your dietary requirements"
    if row["expect_reason_category"] != "diet_conflict":
        assert blanket not in (result.get("reasons_text") or "")


@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r['cluster']}:{r['diet']}:{r['input']}")
def test_audit_matrix_row(row):
    if row["expect_bucket"] == "no_audit":
        pi = detect_intent(row["input"])
        assert pi.intent in ("GREETING", "GENERAL_QUESTION")
        assert not pi.ingredients
        return
    result = run_audit_case(row["diet"], [row["input"]], row.get("allergens") or [])
    _assert_audit_matrix_row(row, result)


@pytest.mark.parametrize("supabase_down", [False, True], ids=lambda v: f"supabase_down={v}")
@pytest.mark.parametrize(
    "row",
    TIER1_ELIGIBLE_ROWS,
    ids=lambda r: f"{r['cluster']}:{r['diet']}:{r['input']}",
)
def test_audit_matrix_tier1_parity(row, supabase_down):
    resolution_cache.clear()
    if supabase_down:
        import core.knowledge.ike2.stores.db as db

        def _raise(*_a, **_k):
            raise RuntimeError("down")

        orig_alias, orig_disambig = db.resolve_alias, db.disambiguate
        db.resolve_alias = _raise
        db.disambiguate = _raise
        try:
            result = run_audit_case(row["diet"], [row["input"]], row.get("allergens") or [])
        finally:
            db.resolve_alias, db.disambiguate = orig_alias, orig_disambig
    else:
        result = run_audit_case(row["diet"], [row["input"]], row.get("allergens") or [])
    _assert_audit_matrix_row(row, result)
