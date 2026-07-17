#!/usr/bin/env python3
"""IKE-2 shadow soak report — query ``ike2_shadow_diffs`` for safety regressions.

Use during staging shadow soak (``IKE2_MODE=shadow``) to confirm
``false_safe_regression`` count stays at zero. Does not require waiting a fixed
number of days; run on demand or via cron.

Examples::

    cd backend && python scripts/ike2_shadow_soak_report.py
    cd backend && python scripts/ike2_shadow_soak_report.py --days 7 --fail-on-regression
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone


def _client():
    from core.knowledge.ingredient_db import get_supabase_config
    from supabase import create_client

    cfg = get_supabase_config()
    if not cfg:
        print("error: Supabase not configured (set SUPABASE_URL and SUPABASE_KEY)", file=sys.stderr)
        sys.exit(2)
    return create_client(cfg.url, cfg.key)


def _fetch_rows(client, *, since: datetime | None):
    q = client.table("ike2_shadow_diffs").select(
        "id, created_at, raw_input, legacy_verdict, ike2_verdict, match, false_safe_regression"
    )
    if since is not None:
        q = q.gte("created_at", since.isoformat())
    return q.order("created_at", desc=True).execute().data or []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IKE-2 shadow soak regression report")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback window in days (0 = all time; default 7)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 if any false_safe_regression rows exist in the window",
    )
    args = parser.parse_args(argv)

    since = None
    if args.days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)

    client = _client()
    rows = _fetch_rows(client, since=since)

    total = len(rows)
    mismatches = sum(1 for r in rows if not r.get("match"))
    false_safe = [r for r in rows if r.get("false_safe_regression")]

    window = f"last {args.days} days" if args.days > 0 else "all time"
    print(f"IKE-2 shadow soak report ({window})")
    print(f"  total diffs logged:     {total}")
    print(f"  verdict mismatches:     {mismatches}")
    print(f"  false_safe_regression:  {len(false_safe)}")

    if false_safe:
        print("\nfalse_safe_regression rows (legacy NOT_SAFE, IKE-2 SAFE):")
        for r in false_safe[:20]:
            print(
                f"  - {r.get('created_at')}  {r.get('raw_input')!r}  "
                f"legacy={r.get('legacy_verdict')} ike2={r.get('ike2_verdict')}"
            )
        if len(false_safe) > 20:
            print(f"  ... and {len(false_safe) - 20} more")

    if args.fail_on_regression and false_safe:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
