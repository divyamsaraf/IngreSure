"""Item 56: derive-hit golden skeleton + precision-per-family from labels."""
from __future__ import annotations

import csv
from pathlib import Path

from scripts.export_derive_hit_sample import (
    COLUMNS,
    GOLDEN_PATH,
    SAMPLE_SIZE,
    collect_derive_hits,
    sample_hits,
    write_csv,
)
from scripts.score_derive_hit_precision import precision_per_family, score_rows

_GOLDEN = Path(__file__).resolve().parent / "golden" / "derive_hit_labels.csv"


def test_golden_csv_exists_with_required_columns():
    assert _GOLDEN.is_file()
    with _GOLDEN.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == list(COLUMNS)
        rows = list(reader)
    assert len(rows) == SAMPLE_SIZE
    for row in rows:
        assert row["atom"].strip()
        assert row["flag"].strip()
        assert row["language"].strip()
        # Empty labels are OK — owner fills them later.
        assert row.get("label", "") in ("", "tp", "fp", "correct", "incorrect")


def test_empty_labels_do_not_fail_scoring():
    rows = [
        {"atom": "milk", "flag": "dairy_source", "context": "ontology", "language": "en", "label": ""},
        {"atom": "wheat", "flag": "gluten_source", "context": "ontology", "language": "en", "label": ""},
    ]
    report = score_rows(rows)
    assert report["labeled"] == 0
    assert report["unlabeled"] == 2
    assert report["precision_per_family"] == {}


def test_precision_per_family_from_labels():
    rows = [
        {"atom": "milk", "flag": "dairy_source", "context": "x", "language": "en", "label": "tp"},
        {"atom": "coconut milk", "flag": "dairy_source", "context": "x", "language": "en", "label": "fp"},
        {"atom": "wheat", "flag": "gluten_source", "context": "x", "language": "en", "label": "tp"},
        {"atom": "buckwheat", "flag": "gluten_source", "context": "x", "language": "en", "label": "fp"},
        {"atom": "oat", "flag": "gluten_source", "context": "x", "language": "en", "label": ""},
    ]
    prec = precision_per_family(rows)
    assert prec["dairy_source"] == 0.5
    assert prec["gluten_source"] == 0.5
    assert "sesame_source" not in prec


def test_collect_and_sample_are_deterministic():
    hits = collect_derive_hits()
    assert len(hits) >= SAMPLE_SIZE
    a = sample_hits(hits, n=SAMPLE_SIZE, seed=56)
    b = sample_hits(hits, n=SAMPLE_SIZE, seed=56)
    assert [ (r["atom"], r["flag"]) for r in a ] == [ (r["atom"], r["flag"]) for r in b ]
    assert len(a) == SAMPLE_SIZE


def test_write_csv_roundtrip(tmp_path: Path):
    rows = sample_hits(collect_derive_hits(), n=5, seed=1)
    out = tmp_path / "hits.csv"
    write_csv(out, rows)
    with out.open(encoding="utf-8", newline="") as fh:
        got = list(csv.DictReader(fh))
    assert got[0].keys() == dict.fromkeys(COLUMNS).keys()
    assert all(r.get("label", "") == "" for r in got)


def test_committed_golden_matches_export_helper_path():
    assert GOLDEN_PATH.resolve() == _GOLDEN.resolve()
