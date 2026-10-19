#!/usr/bin/env python3
"""IKE-2 soak report — query ``ike2_shadow_diffs`` for safety regressions.

Use during staging to confirm the primary + legacy diff logged in
``ike2_shadow_diffs`` keeps ``false_safe_regression`` count at zero. Does not
require waiting a fixed number of days; run on demand or via cron.

Examples::

    cd backend && python scripts/ike2_shadow_soak_report.py
    cd backend && python scripts/ike2_shadow_soak_report.py --days 7 --fail-on-regression
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

try:
    from dotenv import load_dotenv

    load_dotenv(_backend / ".env")
    load_dotenv(_backend.parent / ".env")
except ImportError:
    pass


def _client():
    from core.knowledge.ingredient_db import get_supabase_config
    from supabase import create_client

    cfg = get_supabase_config()
    if not cfg:
        print("error: Supabase not configured (set SUPABASE_URL and SUPABASE_KEY)", file=sys.stderr)
        sys.exit(2)
    return create_client(cfg.url, cfg.key)


def _fetch_rows(
    client,
    *,
    since: datetime | None,
    source_route: str | None,
):
    q = client.table("ike2_shadow_diffs").select(
        "id, created_at, raw_input, legacy_verdict, ike2_verdict, match, "
        "false_safe_regression, source_route, restriction_ids"
    )
    if since is not None:
        q = q.gte("created_at", since.isoformat())
    if source_route:
        q = q.eq("source_route", source_route)
    return q.order("created_at", desc=True).execute().data or []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IKE-2 shadow soak regression report")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback window in days (0 = all time; default 7). Ignored if --since is set.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO timestamp lower bound (e.g. 2026-08-07T23:40:00+00:00). Overrides --days.",
    )
    parser.add_argument(
        "--source-route",
        default=None,
        help="Optional filter: chat | api_evaluate_compliance | api_evaluate_product | test",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 if any false_safe_regression rows exist in the window",
    )
    parser.add_argument(
        "--show-non-regression-mismatches",
        type=int,
        default=0,
        metavar="N",
        help="Print up to N match=false / false_safe=false rows for human review",
    )
    args = parser.parse_args(argv)

    since = None
    if args.since:
        since = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    elif args.days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)

    client = _client()
    rows = _fetch_rows(client, since=since, source_route=args.source_route)

    total = len(rows)
    mismatches = sum(1 for r in rows if not r.get("match"))
    false_safe = [r for r in rows if r.get("false_safe_regression")]
    with_route = sum(1 for r in rows if r.get("source_route"))
    non_reg_mismatch = [
        r for r in rows if (not r.get("match")) and (not r.get("false_safe_regression"))
    ]

    if args.since:
        window = f"since {args.since}"
    elif args.days > 0:
        window = f"last {args.days} days"
    else:
        window = "all time"
    route_note = f", source_route={args.source_route}" if args.source_route else ""
    print(f"IKE-2 shadow soak report ({window}{route_note})")
    print(f"  total diffs logged:     {total}")
    print(f"  with source_route set:  {with_route}")
    print(f"  verdict mismatches:     {mismatches}")
    print(f"  false_safe_regression:  {len(false_safe)}")
    print(f"  match=false non-reg:    {len(non_reg_mismatch)}")

    if false_safe:
        print(
            "\nfalse_safe_regression rows "
            "(IKE-2 SAFE while an active FAIL/WARN rule matches ingredient flags):"
        )
        for r in false_safe[:20]:
            print(
                f"  - {r.get('created_at')}  route={r.get('source_route')!r}  "
                f"rids={r.get('restriction_ids')!r}  {r.get('raw_input')!r}  "
                f"legacy={r.get('legacy_verdict')} ike2={r.get('ike2_verdict')}"
            )
        if len(false_safe) > 20:
            print(f"  ... and {len(false_safe) - 20} more")
        if with_route < total:
            print(
                "\nnote: historical rows (source_route IS NULL) keep pre-fix "
                "false_safe flags; filter with --source-route for the instrumented gate."
            )

    if args.show_non_regression_mismatches > 0 and non_reg_mismatch:
        print(
            f"\nmatch=false / false_safe=false sample "
            f"(up to {args.show_non_regression_mismatches}):"
        )
        for r in non_reg_mismatch[: args.show_non_regression_mismatches]:
            print(
                f"  - {r.get('created_at')}  route={r.get('source_route')!r}  "
                f"rids={r.get('restriction_ids')!r}  {r.get('raw_input')!r}  "
                f"legacy={r.get('legacy_verdict')} ike2={r.get('ike2_verdict')}"
            )

    if args.fail_on_regression and false_safe:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
