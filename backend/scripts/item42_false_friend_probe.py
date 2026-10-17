#!/usr/bin/env python3
"""Cost-side false-friend probe: hazard-looking non-hazards, plain + decorated.

Any Avoid under the implied restriction is a failure (fix + golden).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external

# (base_name, flag, restriction)
PROBES = [
    ("peanut butter", "dairy_source", "dairy_free"),
    ("cocoa butter", "dairy_source", "dairy_free"),
    ("shea butter", "dairy_source", "dairy_free"),
    ("coconut cream", "dairy_source", "dairy_free"),
    ("cream of tartar", "dairy_source", "dairy_free"),
    ("butter beans", "dairy_source", "dairy_free"),
    ("eggplant", "egg_source", "egg_free"),
    ("egg plant", "egg_source", "egg_free"),
    ("crabapple", "shellfish_source", "shellfish_allergy"),
    ("lobster mushroom", "shellfish_source", "shellfish_allergy"),
    ("buckwheat", "gluten_source", "gluten_free"),
    ("rice milk", "dairy_source", "dairy_free"),
    ("oat milk", "dairy_source", "dairy_free"),
    ("almond milk", "dairy_source", "dairy_free"),
    ("soy milk", "dairy_source", "dairy_free"),
    ("nutmeg", "tree_nut_source", "tree_nut_allergy"),
    ("water chestnut", "tree_nut_source", "tree_nut_allergy"),
    ("coconut oil", "tree_nut_source", "tree_nut_allergy"),
    ("groundnut oil", "tree_nut_source", "tree_nut_allergy"),
    ("mustard greens", "mustard_source", "mustard_allergy"),
    ("mustard oil", "mustard_source", "mustard_allergy"),
    ("idli rava", "gluten_source", "gluten_free"),
    ("custard apple", "dairy_source", "dairy_free"),
    ("apple butter", "dairy_source", "dairy_free"),
    ("cream soda", "dairy_source", "dairy_free"),
]

DECORATORS = (
    "",
    "organic {name} smooth",
    "natural {name}",
    "{name} unsalted",
)


def main() -> int:
    rows = []
    for base, flag, rid in PROBES:
        for tmpl in DECORATORS:
            name = tmpl.format(name=base) if tmpl else base
            cache.clear()
            r = resolve(name, None)
            ci = to_compliance_input(r, query_atom=name)
            v = to_external(
                evaluate(
                    [ci],
                    SimpleNamespace(restrictions={rid: "medical"}),
                    rules_module.seeded_rules(),
                ).verdict
            )
            bad = v == "NOT_SAFE"
            rows.append(
                {
                    "name": name,
                    "base": base,
                    "flag": flag,
                    "restriction": rid,
                    "layer": r.resolution_layer,
                    "flag_on_ci": bool(ci.flags.get(flag)),
                    "verdict": v,
                    "false_avoid": bad,
                }
            )
    fails = [r for r in rows if r["false_avoid"]]
    out = {
        "n_probes": len(rows),
        "n_false_avoids": len(fails),
        "false_avoids": fails,
        "all": rows,
        "note": "Any NOT_SAFE = false Avoid on a pantry staple — fix derive + golden.",
    }
    path = _REPO / "docs" / "item42_false_friend_probe.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    md = [
        "# False-friend probe (cost side)",
        "",
        f"Probes: **{len(rows)}**. False Avoids: **{len(fails)}**.",
        "",
        "| Name | Flag | Layer | Flag on CI | Verdict | False Avoid |",
        "|------|------|-------|------------|---------|-------------|",
    ]
    for r in rows:
        if not r["false_avoid"] and r["name"] != r["base"]:
            continue  # keep md readable: bases + failures
        md.append(
            f"| {r['name']} | {r['flag']} | {r['layer']} | {r['flag_on_ci']} | "
            f"{r['verdict']} | {'YES' if r['false_avoid'] else ''} |"
        )
    for r in fails:
        if r["name"] == r["base"]:
            continue
        md.append(
            f"| {r['name']} | {r['flag']} | {r['layer']} | {r['flag_on_ci']} | "
            f"{r['verdict']} | YES |"
        )
    (_REPO / "docs" / "item42_false_friend_probe.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"false_avoids": len(fails), "path": str(path)}, indent=2))
    for f in fails:
        print("FALSE_AVOID", f["name"], f["flag"], f["verdict"])
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
