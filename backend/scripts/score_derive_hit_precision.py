#!/usr/bin/env python3
"""Item 56: precision per derive family from a labeled golden CSV.

Empty labels are ignored (CI skeleton). Owner fills ``label`` with:
  tp / correct  — derive hit is a true positive
  fp / incorrect — derive hit is a false positive

Usage (from backend/):
    python scripts/score_derive_hit_precision.py
    python scripts/score_derive_hit_precision.py --csv tests/ike2/golden/derive_hit_labels.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scripts.export_derive_hit_sample import GOLDEN_PATH

_TP = frozenset({"tp", "correct", "true", "1", "yes"})
_FP = frozenset({"fp", "incorrect", "false", "0", "no"})


def _norm_label(raw: str) -> str | None:
    val = (raw or "").strip().lower()
    if not val:
        return None
    if val in _TP:
        return "tp"
    if val in _FP:
        return "fp"
    raise ValueError(f"unknown label {raw!r}; expected tp/fp/correct/incorrect or empty")


def precision_per_family(rows: list[dict[str, str]]) -> dict[str, float]:
    """Return tp/(tp+fp) per flag family. Families with no labels are omitted."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # tp, fp
    for row in rows:
        kind = _norm_label(row.get("label") or "")
        if kind is None:
            continue
        flag = (row.get("flag") or "").strip()
        if not flag:
            continue
        if kind == "tp":
            counts[flag][0] += 1
        else:
            counts[flag][1] += 1
    out: dict[str, float] = {}
    for flag, (tp, fp) in counts.items():
        denom = tp + fp
        out[flag] = (tp / denom) if denom else 0.0
    return out


def score_rows(rows: list[dict[str, str]]) -> dict:
    labeled = 0
    unlabeled = 0
    for row in rows:
        kind = _norm_label(row.get("label") or "")
        if kind is None:
            unlabeled += 1
        else:
            labeled += 1
    return {
        "labeled": labeled,
        "unlabeled": unlabeled,
        "precision_per_family": precision_per_family(rows),
    }


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=GOLDEN_PATH)
    args = p.parse_args(argv)
    rows = load_csv(args.csv)
    report = score_rows(rows)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
