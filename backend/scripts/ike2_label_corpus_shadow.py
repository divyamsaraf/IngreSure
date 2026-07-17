#!/usr/bin/env python3
"""Label corpus shadow report — legacy vs IKE-2 parity gate (Phase 4 metric C).

Examples::

    cd backend && python scripts/ike2_label_corpus_shadow.py
    cd backend && python scripts/ike2_label_corpus_shadow.py --fail-below-threshold
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

from tests.fixtures.labels.label_corpus_runner import (  # noqa: E402
    SHADOW_MATCH_THRESHOLD,
    run_shadow_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Label corpus legacy/IKE-2 shadow report")
    parser.add_argument(
        "--threshold",
        type=float,
        default=SHADOW_MATCH_THRESHOLD,
        help=f"minimum match rate (default {SHADOW_MATCH_THRESHOLD})",
    )
    parser.add_argument(
        "--fail-below-threshold",
        action="store_true",
        help="exit 1 when match rate is below threshold or false-Safe regressions exist",
    )
    parser.add_argument(
        "--show-mismatches",
        type=int,
        default=10,
        metavar="N",
        help="print up to N mismatches (default 10)",
    )
    args = parser.parse_args(argv)

    report = run_shadow_report(threshold=args.threshold)
    print(json.dumps(report, indent=2))

    if args.show_mismatches and report["mismatches"]:
        print("\nmismatches:", file=sys.stderr)
        for row in report["mismatches"][: args.show_mismatches]:
            print(
                f"  {row.get('id')}: legacy={row['legacy_verdict']} "
                f"ike2={row['ike2_verdict']} input={row['raw_input'][:80]!r}",
                file=sys.stderr,
            )

    if args.fail_below_threshold and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
