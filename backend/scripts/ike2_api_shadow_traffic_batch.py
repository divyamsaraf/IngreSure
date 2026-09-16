#!/usr/bin/env python3
"""Deliberate API evaluate traffic for Item 16 verification.

Sends real ASGI HTTP requests to ``/api/v1/evaluate-compliance`` and
``/api/v1/evaluate-product`` using the label corpus plus a rotating range of
``restriction_ids``. Diffs land in ``ike2_shadow_diffs`` with ``source_route``
set by the evaluate path.

Default ``--mode shadow`` (Section 6). Use ``--mode primary`` for the Prompt-7
primary soak window.

Examples::

    cd backend && python scripts/ike2_api_shadow_traffic_batch.py
    cd backend && python scripts/ike2_api_shadow_traffic_batch.py --mode primary
    cd backend && python scripts/ike2_api_shadow_traffic_batch.py --limit 80
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

try:
    from dotenv import load_dotenv

    load_dotenv(_backend / ".env")
    load_dotenv(_repo / ".env")
except ImportError:
    pass

# Deliberate soak traffic must not be throttled by the public API rate limit.
os.environ["RATE_LIMIT_API_V1_DEFAULT"] = "100000/minute"

CORPUS_PATH = _backend / "tests" / "fixtures" / "labels" / "corpus.jsonl"

# Broad restriction coverage — not just vegan+gluten.
RESTRICTION_ROTATION = [
    ["vegan"],
    ["gluten_free"],
    ["celiac_strict"],
    ["peanut_allergy"],
    ["dairy_free"],
    ["egg_free"],
    ["hindu_vegetarian"],
    ["jain"],
    ["halal"],
    ["kosher"],
    ["vegetarian"],
    ["pescatarian"],
    ["vegan", "gluten_free"],
    ["hindu_vegetarian", "dairy_free"],
]


def _load_corpus(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _pick_restriction_ids(row: dict, index: int) -> list[str]:
    if row.get("restriction_ids"):
        return list(row["restriction_ids"])
    return list(RESTRICTION_ROTATION[index % len(RESTRICTION_ROTATION)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Item 16 API evaluate traffic batch")
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--limit", type=int, default=0, help="Max corpus rows (0 = all)")
    parser.add_argument(
        "--mode",
        choices=("shadow", "primary"),
        default="shadow",
        help="IKE2_MODE for this batch (default shadow; use primary for Prompt-7 soak)",
    )
    parser.add_argument(
        "--skip-product",
        action="store_true",
        help="Only hit evaluate-compliance (skip evaluate-product)",
    )
    args = parser.parse_args(argv)

    os.environ["IKE2_MODE"] = args.mode

    from fastapi.testclient import TestClient

    from app import app

    client = TestClient(app)
    rows = _load_corpus(args.corpus)
    if args.limit > 0:
        rows = rows[: args.limit]

    n_compliance = 0
    n_product = 0
    errors = 0

    for i, row in enumerate(rows):
        raw = (row.get("raw") or "").strip()
        if not raw:
            continue
        rids = _pick_restriction_ids(row, i)
        # evaluate-compliance: pass label as a single ingredient string list entry
        # (same shape many programmatic callers use); engine still decomposes.
        try:
            r = client.post(
                "/api/v1/evaluate-compliance",
                json={
                    "ingredients": [raw],
                    "restriction_ids": rids,
                    "use_api_fallback": False,
                },
            )
            if r.status_code != 200:
                errors += 1
                print(f"compliance FAIL {row.get('id')} status={r.status_code} {r.text[:200]}")
            else:
                n_compliance += 1
        except Exception as exc:
            errors += 1
            print(f"compliance EXC {row.get('id')}: {exc}")

        if not args.skip_product:
            try:
                r = client.post(
                    "/api/v1/evaluate-product",
                    json={
                        "ingredients_text": raw,
                        "restriction_ids": rids,
                        "use_api_fallback": False,
                    },
                )
                if r.status_code != 200:
                    errors += 1
                    print(f"product FAIL {row.get('id')} status={r.status_code} {r.text[:200]}")
                else:
                    n_product += 1
            except Exception as exc:
                errors += 1
                print(f"product EXC {row.get('id')}: {exc}")

    print(
        json.dumps(
            {
                "corpus_rows": len(rows),
                "evaluate_compliance_ok": n_compliance,
                "evaluate_product_ok": n_product,
                "errors": errors,
                "ike2_mode": os.environ.get("IKE2_MODE"),
            },
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
