#!/usr/bin/env python3
"""Classify unmatched atoms from a tagged OFF sample (report-only; ODbL tagged).

Re-resolves with current IKE-2 so L3 (db) and L5 (unknown) stay separate.
Requires read-only Supabase for a true L3 split; without it, L3 is reported
as L3_unavailable rather than invented.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.resolver import resolve  # noqa: E402
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings  # noqa: E402
from core.parsing.translation_pairs import is_translation_pair  # noqa: E402

_ADDITIVE_SUB = re.compile(
    r"^(?:e|ins)\s*\d{2,4}\s*(?:\([ivxlcdm]+\)|\([a-z]\)|[a-z])?$",
    re.I,
)
_FRAGMENT = re.compile(
    r"^(?:ii|iii|iv|vi+|a|b|c|d|i|color|colour|alkali|natural|artificial|freshness)$",
    re.I,
)
_QUALIFIER = re.compile(
    r"(?:processed\s+with\s+alkali|to\s+preserve|color\s+added|natural\s+and\s+artificial)",
    re.I,
)


def _classify_atom(atom: str) -> str:
    a = (atom or "").strip()
    if not a:
        return "fragment"
    if _ADDITIVE_SUB.match(a) or re.search(r"\b(?:e|ins)\s*\d{2,4}\s*\(", a, re.I):
        return "ins_sub_variant"
    if _FRAGMENT.match(a):
        return "fragment"
    if _QUALIFIER.search(a):
        return "qualifier"
    if "/" in a:
        parts = [p.strip() for p in a.split("/") if p.strip()]
        if len(parts) == 2 and is_translation_pair(parts[0], parts[1]):
            return "language"
        return "language"
    if re.search(r"[àâäéèêëïîôùûüçñßæœ]", a, re.I):
        return "language"
    if re.search(r"[\u0600-\u06FF\u0900-\u097F\u4e00-\u9fff]", a):
        return "language"
    return "true_gap"


def _layer(resolved) -> str:
    layer = getattr(resolved, "resolution_layer", "") or ""
    if layer.startswith("L1"):
        return "L1"
    if layer.startswith("L2"):
        return "L2"
    if layer.startswith("L3"):
        if "error" in layer or "unavail" in layer:
            return "L3_unavailable"
        return "L3"
    if layer.startswith("L5") or "unknown" in layer:
        return "L5"
    return layer or "other"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sample",
        type=Path,
        default=_BACKEND / ".local_reports" / "region_dump_ingredients.jsonl",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_BACKEND / ".local_reports" / "region_unmatched_classified.json",
    )
    ap.add_argument("--top", type=int, default=100)
    args = ap.parse_args(argv)

    if not args.sample.exists():
        print(f"missing sample {args.sample}", file=sys.stderr)
        return 2

    os.environ.setdefault("LLM_ENABLED", "false")
    by_market: dict[str, Counter] = defaultdict(Counter)
    unmatched: dict[str, Counter] = defaultdict(Counter)
    class_by_market: dict[str, Counter] = defaultdict(Counter)
    n_lists: Counter = Counter()

    with args.sample.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            market = row.get("market") or "unknown"
            text = row.get("ingredients_text") or ""
            n_lists[market] += 1
            atoms = preprocess_ingredients_to_strings(text)
            for atom in atoms:
                resolved = resolve(atom, region=None)
                bucket = _layer(resolved)
                by_market[market][bucket] += 1
                if bucket in {"L5", "other"} or getattr(resolved, "status", "") == "uncertain":
                    if bucket == "L5" or (
                        getattr(resolved, "trusted", True) is False
                        and not getattr(resolved, "group", None)
                    ):
                        unmatched[market][atom] += 1
                        class_by_market[market][_classify_atom(atom)] += 1

    report = {
        "supabase_url_set": bool(os.environ.get("SUPABASE_URL")),
        "odbl_note": "Tagged OFF sample. Do not promote aliases pending counsel.",
        "lists_per_market": dict(n_lists),
        "layers": {m: dict(c) for m, c in by_market.items()},
        "unmatched_class_counts": {m: dict(c) for m, c in class_by_market.items()},
        "top_unmatched": {
            m: [
                {"atom": a, "n": n, "class": _classify_atom(a)}
                for a, n in c.most_common(args.top)
            ]
            for m, c in unmatched.items()
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "wrote": str(args.out),
        "lists": dict(n_lists),
        "layers": report["layers"],
        "classes": report["unmatched_class_counts"],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
