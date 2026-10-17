#!/usr/bin/env python3
"""Measure residual conservation losses: SAFE before/after label backstops.

Rebuilds the residual miss set from the local OFF product cache (same texts
the 380-list audit used), evaluates the affected medical profile per lost
hazard, then re-evaluates with raw_label + parse-quality ceiling.

Writes ``backend/.local_reports/item44_residual_backstop.json``.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.normalization.parser import flatten_ingredients
from core.parsing.hazard_lexicon import conservation_misses
from core.parsing.parse_quality import assess_parse_quality
from item44_parser_conservation import _classify_raw, _load_cache

_OUT = _BACKEND / ".local_reports" / "item44_residual_backstop.json"

# Lost lexicon class -> profile restriction that must not firm-SAFE.
_CLASS_TO_RESTRICTION = {
    "peanut": "peanut_allergy",
    "gluten": "gluten_free",
    "dairy": "dairy_free",
    "egg": "egg_free",
    "soy": "soy_allergy",
    "sesame": "sesame_allergy",
    "fish": "fish_allergy",
    "shellfish": "shellfish_allergy",
    "tree_nut": "tree_nut_allergy",
}


def _inputs(atoms: list[str]):
    return [to_compliance_input(resolve(a, None), query_atom=a) for a in atoms]


def main() -> int:
    cache = _load_cache()
    rules = rules_module.seeded_rules()
    misses = []
    for code, prod in cache.items():
        raw = (prod.get("ingredients_text") or "").strip()
        if not raw:
            continue
        atoms = [a for a in flatten_ingredients(raw) if a]
        lost = conservation_misses(raw, atoms)
        if not lost:
            continue
        patterns = _classify_raw(raw)
        quality = assess_parse_quality(raw, atoms)
        row = {
            "code": code,
            "market": prod.get("market") or prod.get("countries_tags"),
            "lost_hazards": sorted(lost),
            "patterns": patterns,
            "parse_quality_reasons": list(quality.reasons),
            "raw_excerpt": raw[:240],
            "n_atoms": len(atoms),
            "evals": [],
        }
        for cls in sorted(lost):
            rid = _CLASS_TO_RESTRICTION.get(cls)
            if not rid:
                continue
            profile = SimpleNamespace(restrictions={rid: "medical"})
            cis = _inputs(atoms)
            before = evaluate(cis, profile, rules)
            after = evaluate(cis, profile, rules, raw_label=raw, parsed_atoms=atoms)
            row["evals"].append(
                {
                    "hazard": cls,
                    "restriction": rid,
                    "before": to_external(before.verdict),
                    "after": to_external(after.verdict),
                    "before_int": int(before.verdict),
                    "after_int": int(after.verdict),
                }
            )
        misses.append(row)

    # Per list: SAFE for any affected profile before / after
    safe_before = 0
    safe_after = 0
    pair_counts = Counter()
    pattern_counts = Counter()
    hazard_counts = Counter()
    quality_reason_counts = Counter()
    for m in misses:
        for p in m["patterns"]:
            pattern_counts[p] += 1
        for h in m["lost_hazards"]:
            hazard_counts[h] += 1
        for r in m["parse_quality_reasons"]:
            quality_reason_counts[r] += 1
        list_safe_b = any(e["before"] == "SAFE" for e in m["evals"])
        list_safe_a = any(e["after"] == "SAFE" for e in m["evals"])
        if list_safe_b:
            safe_before += 1
        if list_safe_a:
            safe_after += 1
        for e in m["evals"]:
            pair_counts[f"{e['before']}->{e['after']}"] += 1

    report = {
        "n_cache_products_scanned": len(cache),
        "n_residual_miss_lists": len(misses),
        "safe_list_evals_any_affected_profile_before": safe_before,
        "safe_list_evals_any_affected_profile_after": safe_after,
        "target_safe_after": 0,
        "verdict_transitions": dict(pair_counts),
        "pattern_counts": dict(pattern_counts),
        "hazard_miss_counts": dict(hazard_counts),
        "parse_quality_reason_counts": dict(quality_reason_counts),
        "backstops": {
            "raw_string_hazard_sweep": "implemented",
            "parse_quality_ceiling": "implemented",
            "attribution": "label text",
        },
        "misses_sample": [
            {
                "code": m["code"],
                "lost_hazards": m["lost_hazards"],
                "patterns": m["patterns"],
                "parse_quality_reasons": m["parse_quality_reasons"],
                "evals": m["evals"],
                "raw_excerpt": m["raw_excerpt"],
            }
            for m in misses[:80]
        ],
        "still_safe_after": [
            {
                "code": m["code"],
                "lost_hazards": m["lost_hazards"],
                "evals": m["evals"],
                "raw_excerpt": m["raw_excerpt"],
            }
            for m in misses
            if any(e["after"] == "SAFE" for e in m["evals"])
        ][:40],
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "n_residual": report["n_residual_miss_lists"],
                "safe_before": safe_before,
                "safe_after": safe_after,
                "transitions": dict(pair_counts),
                "patterns": dict(pattern_counts),
                "path": str(_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
