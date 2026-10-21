#!/usr/bin/env python3
"""Item 39: shrink the grandfathered orthographic baseline (allergy first).

Drops allergy-restriction triples that no longer reproduce SAFE↔UNCERTAIN.
Does not rewrite ontology.json.

Usage (from backend/):
    python scripts/shrink_orthographic_baseline.py --dry-run
    python scripts/shrink_orthographic_baseline.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.orthographic_variants import (
    ORTHO_RESTRICTIONS,
    reviewed_safe_uncertain,
)

_REVIEWED_PATH = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "knowledge"
    / "ike2"
    / "orthographic_safe_uncertain_baseline.json"
)

ALLERGY_RESTRICTIONS = frozenset({
    "sulfite_sensitive",
    "gluten_free",
    "dairy_free",
    "egg_free",
    "fish_allergy",
    "shellfish_allergy",
    "soy_allergy",
    "sesame_allergy",
    "mustard_allergy",
    "celery_allergy",
    "lupin_allergy",
    "peanut_allergy",
    "tree_nut_allergy",
})


def stale_allergy_entries(
    triples: Iterable[tuple[str, str, str]],
    *,
    still_asymmetric: Callable[[str, str, str], bool],
) -> list[tuple[str, str, str]]:
    """Allergy triples that no longer reproduce SAFE↔UNCERTAIN (safe to drop)."""
    stale: list[tuple[str, str, str]] = []
    for left, right, rid in triples:
        if rid not in ALLERGY_RESTRICTIONS:
            continue
        if not still_asymmetric(left, right, rid):
            stale.append((left, right, rid))
    return stale


def _pair_still_asymmetric(left: str, right: str, restriction: str) -> bool:
    from types import SimpleNamespace

    from core.knowledge.ike2 import rules as rules_module
    from core.knowledge.ike2.compliance import evaluate
    from core.knowledge.ike2.resolver import resolve
    from core.knowledge.ike2.seam import to_compliance_input
    from core.knowledge.ike2.verdict import to_external

    def _verdict(name: str) -> str:
        r = resolve(name, None)
        ci = to_compliance_input(r, query_atom=name)
        return to_external(
            evaluate(
                [ci],
                SimpleNamespace(restrictions={restriction: "medical"}),
                rules_module.seeded_rules(),
            ).verdict
        )

    return {_verdict(left), _verdict(right)} == {"SAFE", "UNCERTAIN"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true", default=True)
    args = p.parse_args(argv)
    current = sorted(reviewed_safe_uncertain())
    stale = stale_allergy_entries(current, still_asymmetric=_pair_still_asymmetric)
    keep = [t for t in current if t not in set(stale)]
    print(
        json.dumps(
            {
                "before": len(current),
                "stale_allergy_dropped": len(stale),
                "after": len(keep),
                "allergy_restrictions": sorted(ALLERGY_RESTRICTIONS),
                "sample_dropped": stale[:20],
            },
            indent=2,
        )
    )
    if args.apply and stale:
        payload = {
            "note": (
                "Grandfathered baseline snapshot of SAFE↔UNCERTAIN orthographic "
                "asymmetries (ratchet, not a written per-pair review). "
                "Item 39: stale allergy triples that no longer reproduce were dropped."
            ),
            "pairs": [list(t) for t in keep],
        }
        _REVIEWED_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        reviewed_safe_uncertain.cache_clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
