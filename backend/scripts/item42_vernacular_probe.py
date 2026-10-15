#!/usr/bin/env python3
"""One-off Indian vernacular probe → fold hits into Item 12 lexicon.

Resolves common Indian grocery names under the implied restriction and reports
SAFE where the hazard flag is absent on the compliance input.
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

# name → (flag, restriction)
PROBES = [
    # gluten
    ("atta", "gluten_source", "gluten_free"),
    ("maida", "gluten_source", "gluten_free"),
    ("sooji", "gluten_source", "gluten_free"),
    ("suji", "gluten_source", "gluten_free"),
    ("rava", "gluten_source", "gluten_free"),
    ("dalia", "gluten_source", "gluten_free"),
    ("roti", "gluten_source", "gluten_free"),
    ("chapati", "gluten_source", "gluten_free"),
    ("chapatti", "gluten_source", "gluten_free"),
    ("paratha", "gluten_source", "gluten_free"),
    ("naan", "gluten_source", "gluten_free"),
    ("puri", "gluten_source", "gluten_free"),
    # dairy
    ("paneer", "dairy_source", "dairy_free"),
    ("dahi", "dairy_source", "dairy_free"),
    ("curd", "dairy_source", "dairy_free"),
    ("khoa", "dairy_source", "dairy_free"),
    ("mawa", "dairy_source", "dairy_free"),
    ("lassi", "dairy_source", "dairy_free"),
    ("chaas", "dairy_source", "dairy_free"),
    ("malai", "dairy_source", "dairy_free"),
    # egg
    ("anda", "egg_source", "egg_free"),
    # tree nut
    ("kaju", "tree_nut_source", "tree_nut_allergy"),
    ("badam", "tree_nut_source", "tree_nut_allergy"),
    ("pista", "tree_nut_source", "tree_nut_allergy"),
    ("akhrot", "tree_nut_source", "tree_nut_allergy"),
    # sesame / mustard
    ("til", "sesame_source", "sesame_allergy"),
    ("rai", "mustard_source", "mustard_allergy"),
    ("sarson", "mustard_source", "mustard_allergy"),
]


def main() -> int:
    rows = []
    for name, flag, rid in PROBES:
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
        rows.append(
            {
                "name": name,
                "flag": flag,
                "restriction": rid,
                "layer": r.resolution_layer,
                "trusted": bool(ci.trusted),
                "flag_on_ci": bool(ci.flags.get(flag)),
                "verdict": v,
                "gap": v == "SAFE" and not ci.flags.get(flag),
            }
        )
    gaps = [r for r in rows if r["gap"]]
    out = {
        "n_probes": len(rows),
        "n_gaps_safe_flag_absent": len(gaps),
        "gaps": gaps,
        "all": rows,
        "note": (
            "SAFE + flag absent = vernacular blind spot. Fold gap tokens into "
            "Item 12 FAMILY_LEX / ontology / regional remap."
        ),
    }
    path = _REPO / "docs" / "item42_vernacular_probe.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    md = [
        "# Indian vernacular probe",
        "",
        f"Probes: **{len(rows)}**. Gaps (SAFE, flag absent): **{len(gaps)}**.",
        "",
        "| Name | Flag | Layer | Trusted | Flag on CI | Verdict | Gap |",
        "|------|------|-------|---------|------------|---------|-----|",
    ]
    for r in rows:
        md.append(
            f"| {r['name']} | {r['flag']} | {r['layer']} | {r['trusted']} | "
            f"{r['flag_on_ci']} | {r['verdict']} | {'YES' if r['gap'] else ''} |"
        )
    (_REPO / "docs" / "item42_vernacular_probe.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"gaps": len(gaps), "path": str(path)}, indent=2))
    for g in gaps:
        print("GAP", g)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
