#!/usr/bin/env python3
"""One-shot true-only asserted_flags backfill for data/ontology.json (Item 11)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "backend"))

from core.knowledge.ike2.etl.backfill_asserted_flags import (  # noqa: E402
    backfill_ontology_ingredients,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=_REPO / "data" / "ontology.json",
        help="ontology.json path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print counts only; do not write",
    )
    args = parser.parse_args()
    data = json.loads(args.path.read_text(encoding="utf-8"))
    ingredients = list(data.get("ingredients") or [])
    updated = backfill_ontology_ingredients(ingredients)
    changed = sum(
        1
        for before, after in zip(ingredients, updated)
        if (before.get("asserted_flags") or []) != (after.get("asserted_flags") or [])
    )
    nonempty = sum(1 for row in updated if row.get("asserted_flags"))
    print(f"rows={len(updated)} changed={changed} with_asserted={nonempty}")
    if args.dry_run:
        return 0
    data["ingredients"] = updated
    args.path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
