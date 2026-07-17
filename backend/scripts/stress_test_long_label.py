#!/usr/bin/env python3
"""Stress test: 200+ ingredient label with junk text — legacy vs IKE-2.

Usage (from backend/):
    python scripts/stress_test_long_label.py
    python scripts/stress_test_long_label.py --ingredients 250 --iterations 5
    python scripts/stress_test_long_label.py --seeded-rules   # CI-deterministic IKE-2 rules
    python scripts/stress_test_long_label.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

from dotenv import load_dotenv

load_dotenv(_backend / ".env")

from tests.fixtures.labels.stress_label import (  # noqa: E402
    build_stress_label,
    run_stress_suite,
    run_user_input_stress,
)


def _print_human(report: dict) -> None:
    print("=" * 72)
    print("LONG LABEL STRESS TEST — Legacy vs IKE-2")
    print("=" * 72)
    print(f"Label size:        {report['label_chars']:,} chars")
    print(f"Decomposed atoms:  {report['decomposed_atoms']} (target {report['ingredient_target']}+)")
    print()
    print("Latency (vegan profile, {} runs):".format(report["iterations"]))
    leg = report["latency"]["legacy_ms"]
    ik = report["latency"]["ike2_ms"]
    print(f"  Legacy  p50={leg['p50']:.0f}ms  p95={leg['p95']:.0f}ms  mean={leg['mean']:.0f}ms")
    print(f"  IKE-2   p50={ik['p50']:.0f}ms  p95={ik['p95']:.0f}ms  mean={ik['mean']:.0f}ms")
    print()
    print("Per-profile comparison:")
    for row in report["profiles"]:
        leg_v = row["legacy"]["verdict"]
        ik_v = row["ike2"]["verdict"]
        match = "OK" if row["verdict_match"] else "MISMATCH"
        fs = " FALSE-SAFE!" if row["false_safe_regression"] else ""
        atoms = row["legacy"]["atom_count"]
        print(
            f"  {row['profile_id']:<14} legacy={leg_v:<10} ike2={ik_v:<10} "
            f"atoms={atoms} {match}{fs} "
            f"(Δlatency {row['latency_delta_ms']:+.0f}ms)"
        )
        if not row["verdict_match"]:
            print(
                f"    legacy triggered: {row['legacy']['triggered_ingredients'][:8]}"
            )
            print(
                f"    ike2 matched:     {row['ike2']['matched_contains'][:8]}"
            )
    print()
    s = report["summary"]
    print(
        f"Verdict match rate: {s['verdict_match_rate']:.0%}  "
        f"false-Safe regressions: {s['false_safe_regressions']}  "
        f"atom parity: {s['atom_parity_all_profiles']}"
    )
    if s["mismatch_profiles"]:
        print(f"Mismatched profiles: {', '.join(s['mismatch_profiles'])}")
    print("=" * 72)


def _print_user_input(report: dict) -> None:
    print()
    print("USER INPUT SCENARIOS (intent detector → legacy + IKE-2):")
    print("-" * 72)
    for row in report["scenarios"]:
        match = (
            "OK"
            if row["verdict_match"]
            else ("n/a" if row["verdict_match"] is None else "MISMATCH")
        )
        fs = " FALSE-SAFE!" if row["false_safe_regression"] else ""
        print(
            f"  {row['scenario_id']:<22} intent={row['intent']:<18} "
            f"ingredients={row['ingredient_count']:<4} "
            f"legacy={str(row['legacy_verdict']):<10} ike2={str(row['ike2_verdict']):<10} "
            f"{match}{fs}"
        )
        lat = row["latency_ms"]
        print(
            f"    latency: intent={lat['intent']:.0f}ms  "
            f"compliance={lat['compliance']:.0f}ms  total={lat['total']:.0f}ms"
        )
    us = report["summary"]
    print(
        f"  User-input verdict match: {us['verdict_match_rate']:.0%}  "
        f"false-Safe: {us['false_safe_regressions']}"
    )
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Long label legacy vs IKE-2 stress test")
    parser.add_argument("--ingredients", type=int, default=240, help="ontology names in list")
    parser.add_argument("--iterations", type=int, default=3, help="latency sample runs")
    parser.add_argument(
        "--seeded-rules",
        action="store_true",
        help="use in-code IKE-2 rules (deterministic; no Supabase)",
    )
    parser.add_argument("--json", action="store_true", help="print JSON report only")
    parser.add_argument(
        "--fail-on-false-safe",
        action="store_true",
        help="exit 1 if any false-Safe regression",
    )
    args = parser.parse_args(argv)

    # Smoke: label builds
    _ = build_stress_label(args.ingredients)

    report = run_stress_suite(
        ingredient_count=args.ingredients,
        iterations=args.iterations,
        use_seeded_rules=args.seeded_rules,
    )
    user_report = run_user_input_stress(
        ingredient_count=args.ingredients,
        use_seeded_rules=args.seeded_rules,
    )

    if args.json:
        print(json.dumps({"label_stress": report, "user_input": user_report}, indent=2))
    else:
        _print_human(report)
        _print_user_input(user_report)

    if args.fail_on_false_safe and (
        report["summary"]["false_safe_regressions"]
        or user_report["summary"]["false_safe_regressions"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
