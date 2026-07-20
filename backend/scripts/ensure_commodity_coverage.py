#!/usr/bin/env python3
"""
Productize commodity coverage: promote dumps → ontology, then fail on drift.

Root cause this guards against:
  Staging/layer1 dumps contain foods, but chat never sees them until someone
  remembers to promote short chat keys into data/ontology.json.

Usage (repo root or backend/):
  python backend/scripts/ensure_commodity_coverage.py
  python backend/scripts/ensure_commodity_coverage.py --check-only

CI should run without --check-only so promote is applied, then ``git diff
--exit-code`` on ontology proves the committed tree already includes promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scripts.promote_commodity_coverage import promote  # noqa: E402

_VARIANT_RECALL = _REPO / "data" / "commodity_seed_lists" / "variant_recall.txt"


def _resolve_rate_for_usda_raw_heads(limit: int = 200) -> tuple[int, int, list[str]]:
    """Sample simple USDA ', raw' plant heads and measure resolve hit rate."""
    from core.knowledge.ike2.commodity_head import simple_commodity_head
    from core.knowledge.ike2.resolution_cache import clear
    from core.knowledge.ike2.resolver import resolve
    from core.knowledge.ike2.stores.local_ontology import reset_cache

    staging = _REPO / "data" / "usda_staging.json"
    if not staging.exists():
        return 0, 0, []
    data = json.loads(staging.read_text(encoding="utf-8"))
    heads: list[str] = []
    seen: set[str] = set()
    for row in data.get("ingredients") or []:
        if not row.get("plant_origin"):
            continue
        cat = (row.get("_usda_category") or "").lower()
        if not any(
            cat.startswith(c)
            for c in (
                "vegetables",
                "fruits",
                "legumes",
                "spices",
                "cereal",
                "nut and seed",
            )
        ):
            continue
        head = simple_commodity_head(row.get("canonical_name") or "")
        if not head or head in seen:
            continue
        seen.add(head)
        heads.append(head)
        if len(heads) >= limit:
            break

    clear()
    reset_cache()
    ok = 0
    misses: list[str] = []
    for h in heads:
        r = resolve(h, None)
        if r.status == "resolved" and r.trusted:
            ok += 1
        else:
            misses.append(h)
    return ok, len(heads), misses


def _variant_recall_rate() -> tuple[int, int, list[str]]:
    from core.knowledge.ike2.resolution_cache import clear
    from core.knowledge.ike2.resolver import resolve
    from core.knowledge.ike2.stores.local_ontology import reset_cache
    from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache

    if not _VARIANT_RECALL.exists():
        return 0, 0, []
    items = [
        x.strip()
        for x in _VARIANT_RECALL.read_text(encoding="utf-8").replace("\n", " ").split(",")
        if x.strip()
    ]
    clear()
    reset_cache()
    reset_variant_alias_cache()
    ok = 0
    misses: list[str] = []
    for raw in items:
        r = resolve(raw, None)
        if r.status == "resolved" and r.trusted:
            ok += 1
        else:
            misses.append(raw)
    return ok, len(items), misses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not write ontology; only report resolve rates",
    )
    parser.add_argument(
        "--min-usda-head-rate",
        type=float,
        default=0.85,
        help="Minimum fraction of sampled USDA ', raw' heads that must resolve",
    )
    parser.add_argument(
        "--min-variant-recall",
        type=float,
        default=0.85,
        help="Minimum fraction of variant_recall.txt items that must resolve",
    )
    args = parser.parse_args()
    failed = False

    if not args.check_only:
        report = promote(dry_run=False)
        print(json.dumps({
            "promoted": True,
            "before": report["before_count"],
            "after": report["after_count"],
            "usda_extracted": report["usda_commodities_extracted"],
            "grocery_seed": report["grocery_seed_count"],
            "variant_aliases_attached": report.get("variant_aliases_attached", 0),
        }, indent=2))

    ok, total, misses = _resolve_rate_for_usda_raw_heads()
    rate = (ok / total) if total else 1.0
    print(json.dumps({
        "usda_raw_heads_resolved": ok,
        "usda_raw_heads_sampled": total,
        "resolve_rate": round(rate, 4),
        "miss_sample": misses[:25],
    }, indent=2))
    if total and rate < args.min_usda_head_rate:
        print(
            f"FAIL: USDA head resolve rate {rate:.2%} < required {args.min_usda_head_rate:.0%}",
            file=sys.stderr,
        )
        failed = True

    vok, vtotal, vmiss = _variant_recall_rate()
    vrate = (vok / vtotal) if vtotal else 1.0
    print(json.dumps({
        "variant_recall_resolved": vok,
        "variant_recall_sampled": vtotal,
        "variant_recall_rate": round(vrate, 4),
        "variant_miss_sample": vmiss[:25],
    }, indent=2))
    if vtotal and vrate < args.min_variant_recall:
        print(
            f"FAIL: variant recall {vrate:.2%} < required {args.min_variant_recall:.0%}",
            file=sys.stderr,
        )
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
