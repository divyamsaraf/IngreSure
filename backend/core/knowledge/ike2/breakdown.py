"""Per-restriction view of an evaluate() result for the B2B body.

Category comes from data/restrictions.json, not ike2_restriction_rules.category
(that column is the restriction id). The label is response data. It is not
written into the severity string evaluate() reads.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.knowledge.ike2.verdict import Verdict, aggregate, to_external

_CATALOG = Path(__file__).resolve().parents[4] / "data" / "restrictions.json"


@lru_cache(maxsize=1)
def restriction_categories() -> dict[str, str]:
    raw = json.loads(_CATALOG.read_text(encoding="utf-8"))
    out = {}
    for row in raw.get("restrictions") or []:
        rid = row.get("id")
        if rid:
            out[rid] = row.get("category")
    return out


def by_restriction(result, restriction_ids) -> list[dict]:
    """One external verdict per requested restriction. Most severe cell wins."""
    grouped: dict[str, list] = {}
    for (_name, rid), verdict in (getattr(result, "breakdown", None) or {}).items():
        grouped.setdefault(rid, []).append(verdict)
    categories = restriction_categories()
    rows = []
    for rid in restriction_ids or []:
        cells = grouped.get(rid) or []
        verdict = aggregate(cells) if cells else Verdict.UNCERTAIN
        rows.append({
            "restriction_id": rid,
            "category": categories.get(rid),
            "verdict": to_external(verdict),
        })
    return rows


def restriction_matrix(result) -> list[dict]:
    """Opt-in ingredient × restriction cells."""
    categories = restriction_categories()
    rows = []
    for (name, rid), verdict in (getattr(result, "breakdown", None) or {}).items():
        rows.append({
            "ingredient": name,
            "restriction_id": rid,
            "category": categories.get(rid),
            "verdict": to_external(verdict),
        })
    return rows
