#!/usr/bin/env python3
"""Same-seed local reference recipe for Item 29 / Item 44 parity.

PR #17 owns ``item44_prod_parity.py``. This wrapper does not edit that file.
It documents --and optionally invokes -- the PR #17 flags:

    --write-reference <path>
    --reference-json <path>
    --same-seed

Production's database is the ontology seed, not the ~6,800-group local bulk
corpus. The 95% agreement bar is valid only when the reference and the
candidate share that ontology seed.

This script never calls the production API host. It never migrates or seeds a
remote database.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
_PARITY = _BACKEND / "scripts" / "item44_prod_parity.py"
_DEFAULT_REF = _BACKEND / ".local_reports" / "item44_same_seed_reference.json"
_RECIPE_OUT = _REPO / "docs" / "item29" / "same_seed_recipe.json"
_PROD_HOST_MARKERS = ("ingresure-api.gleeze.com", "supabase.co")
_PR17_FLAGS = ("--write-reference", "--reference-json", "--same-seed")


def _parity_source() -> str:
    return _PARITY.read_text(encoding="utf-8") if _PARITY.is_file() else ""


def _flag_status() -> dict[str, bool]:
    text = _parity_source()
    return {flag: flag in text for flag in _PR17_FLAGS}


def _recipe(flags: dict[str, bool]) -> dict:
    ref = "backend/.local_reports/item44_same_seed_reference.json"
    return {
        "purpose": (
            "Build a local Item 44 reference against an ontology-only seed, "
            "then score a candidate with the PR #17 same-seed flags."
        ),
        "pr17_owns": "backend/scripts/item44_prod_parity.py",
        "pr17_flags_present_in_this_tree": flags,
        "production_seed": "data/ontology.json via python scripts/seed_ike2_ontology.py",
        "do_not": [
            "Use a local DB that already has ~6,800 bulk groups as the 95% bar",
            "Call https://ingresure-api.gleeze.com from this wrapper",
            "Migrate or seed a remote Supabase project from this recipe",
        ],
        "local_steps": [
            {
                "step": 1,
                "what": "Local Supabase only (127.0.0.1). Apply migrations through 20261014000000.",
                "cmd": "supabase db reset   # local CLI project_id=ingresure — not remote",
            },
            {
                "step": 2,
                "what": "Seed the production ontology only. No layer1 bulk_inject.",
                "cmd": "cd backend && python scripts/seed_ike2_ontology.py",
            },
            {
                "step": 3,
                "what": "Write the same-seed reference (PR #17 --write-reference).",
                "cmd": (
                    "cd backend && python scripts/item44_prod_parity.py "
                    f"--write-reference {ref} --limit 0"
                ),
            },
            {
                "step": 4,
                "what": (
                    "Score a candidate API that shares the ontology seed. "
                    "Hold 95% only with --same-seed. Hard gates: zero "
                    "candidate-SAFE where reference is NOT_SAFE/UNCERTAIN; zero 5xx."
                ),
                "cmd": (
                    "PROD_API_BASE=http://127.0.0.1:8001 "
                    "python scripts/item44_prod_parity.py "
                    f"--reference-json {ref} --same-seed --sleep 1.2"
                ),
            },
        ],
        "conceptual_flags": {
            "--write-reference": "Dump local TestClient verdicts as the ontology-seed reference",
            "--reference-json": "Compare a candidate against that reference instead of a live local eval",
            "--same-seed": "Enables the 95% agreement gate; invalid unless both sides used ontology seed",
        },
    }


def _refuse_remote(url: str | None) -> None:
    raw = (url or "").strip().lower()
    if not raw:
        return
    if any(m in raw for m in _PROD_HOST_MARKERS):
        raise SystemExit(
            f"refusing remote/production host in this wrapper: {url!r}. "
            "Item 29 is local-only."
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Item 29 same-seed reference recipe")
    parser.add_argument("--emit-recipe", action="store_true", help="Write recipe JSON")
    parser.add_argument(
        "--invoke-write-reference",
        action="store_true",
        help="Run local --write-reference only if PR #17 flags exist (never production).",
    )
    parser.add_argument(
        "--reference-json",
        type=Path,
        default=_DEFAULT_REF,
        help="Reference path passed through to item44_prod_parity.py",
    )
    args = parser.parse_args(argv)

    _refuse_remote(os.environ.get("PROD_API_BASE"))
    _refuse_remote(os.environ.get("SUPABASE_URL"))

    flags = _flag_status()
    recipe = _recipe(flags)
    print(json.dumps(recipe, indent=2))

    if args.emit_recipe:
        _RECIPE_OUT.parent.mkdir(parents=True, exist_ok=True)
        _RECIPE_OUT.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
        print("wrote", _RECIPE_OUT)

    if args.invoke_write_reference:
        if not all(flags.values()):
            print(
                "PR #17 flags are not in this tree's item44_prod_parity.py yet. "
                "Do not edit that file from Item 29. Re-run after PR #17 lands.",
                file=sys.stderr,
            )
            return 2
        cmd = [
            sys.executable,
            str(_PARITY),
            "--write-reference",
            str(args.reference_json),
            "--limit",
            "0",
        ]
        print("local invoke:", " ".join(cmd))
        return subprocess.call(cmd, cwd=str(_BACKEND))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
