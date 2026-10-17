"""Preventive choke-point guard: full-boolean dumps must not re-pollute asserted_flags."""
from __future__ import annotations

import ast
from pathlib import Path

from core.knowledge.ike2.e_number_catalog import entry_to_ike2_row
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.validate import mark_curated_asserted_negatives, validate_rows


def _false_asserted(row: dict) -> list[str]:
    return [f for f in (row.get("asserted_flags") or []) if not row.get(f)]


def test_entry_to_ike2_row_asserted_true_only():
    row = entry_to_ike2_row(
        {
            "e_code": "E221",
            "canonical_name": "sodium sulphite",
            "sulphite_source": True,
            "synthetic": True,
            "plant_origin": False,
            "animal_origin": False,
        }
    )
    row["classification_method"] = "bulk:e_number_catalog"
    assert _false_asserted(row) == []
    ok, rejects = validate_rows([row])
    assert rejects == []
    assert ok


def test_ontology_row_through_adapt_respects_curated_asserted():
    raw = {f: False for f in BOOL_FLAGS}
    raw.update(
        {
            "canonical_name": "einkorn",
            "plant_origin": True,
            "gluten_source": True,
            "asserted_flags": ["plant_origin", "gluten_source"],
            "aliases": [],
        }
    )
    row, _ = map_record(raw, "ontology", "AUTO_CLASSIFIED")
    assert _false_asserted(row) == []
    assert "gluten_source" in row["asserted_flags"]
    ok, rejects = validate_rows([row])
    assert rejects == []


def test_full_boolean_dump_through_adapt_asserts_true_only():
    """Full-block signature → adapt asserts trues only (no validate quarantine needed)."""
    raw = {f: False for f in BOOL_FLAGS}
    raw.update({"canonical_name": "mystery additive", "plant_origin": True, "aliases": []})
    row, _ = map_record(raw, "usda", "AUTO_CLASSIFIED")
    assert _false_asserted(row) == []
    assert "plant_origin" in row["asserted_flags"]
    ok, rejects = validate_rows([row])
    assert rejects == []


def test_polluted_asserted_flags_quarantined_at_validate():
    row = {
        "canonical_name": "polluted",
        "plant_origin": True,
        "asserted_flags": [
            "plant_origin",
            "dairy_source",
            "egg_source",
            "gluten_source",
            "soy_source",
        ],
        "dairy_source": False,
        "egg_source": False,
        "gluten_source": False,
        "soy_source": False,
    }
    ok, rejects = validate_rows([row])
    assert ok == []
    # Registry fires before the >3 count backstop.
    assert rejects[0]["violated_constraint"] == "asserted_flags_unreviewed_negative"


def test_curated_asserted_negatives_relaxes_count_not_registry():
    """curated escape relaxes >3 only; each false must still be reviewed."""
    # hemp milk dairy clear is on the registry; egg/gluten/soy are not.
    row = {
        "canonical_name": "hemp milk",
        "plant_origin": True,
        "dairy_source": False,
        "egg_source": False,
        "gluten_source": False,
        "soy_source": False,
        "asserted_flags": [
            "plant_origin",
            "dairy_source",
            "egg_source",
            "gluten_source",
            "soy_source",
        ],
    }
    row = mark_curated_asserted_negatives(row)
    ok, rejects = validate_rows([row])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "asserted_flags_unreviewed_negative"


def test_reviewed_negative_on_registry_passes():
    row = {
        "canonical_name": "butter without salt",
        "animal_origin": True,
        "dairy_source": True,
        "egg_source": False,
        "asserted_flags": ["animal_origin", "dairy_source", "egg_source"],
    }
    ok, rejects = validate_rows([row])
    assert rejects == []
    assert ok


def test_three_or_fewer_asserted_falses_allowed():
    # rice semolina × gluten_source is on the reviewed-negatives registry (stem).
    row = {
        "canonical_name": "rice semolina",
        "plant_origin": True,
        "gluten_source": False,
        "asserted_flags": ["plant_origin", "gluten_source"],
    }
    ok, rejects = validate_rows([row])
    assert rejects == []
    assert ok


def test_curated_asserted_negatives_true_only_via_mark_helper():
    """Only mark_curated_asserted_negatives may assign True (submit_induced auto=False shape)."""
    core = Path(__file__).resolve().parents[2] / "core"
    assignments = []
    for path in core.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if (
                        isinstance(t, ast.Subscript)
                        and isinstance(t.slice, ast.Constant)
                        and t.slice.value == "curated_asserted_negatives"
                    ):
                        if isinstance(node.value, ast.Constant) and node.value.value is True:
                            assignments.append((str(path), node.lineno))
            if isinstance(node, ast.Call):
                # dict(curated_asserted_negatives=True) / mark helper body
                for kw in node.keywords or []:
                    if (
                        kw.arg == "curated_asserted_negatives"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        assignments.append((str(path), node.lineno))
    # Sole allowed assignment: inside mark_curated_asserted_negatives in validate.py
    validate_py = str(core / "knowledge" / "ike2" / "etl" / "validate.py")
    assert assignments, "expected mark_curated_asserted_negatives assignment"
    assert all(p == validate_py for p, _ in assignments), assignments
    # And bulk_inject must call the helper (not invent its own True)
    inject_src = (core / "knowledge" / "ike2" / "etl" / "bulk_inject.py").read_text(encoding="utf-8")
    assert "mark_curated_asserted_negatives" in inject_src
