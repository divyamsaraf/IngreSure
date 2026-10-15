#!/usr/bin/env python3
"""Item 42 kind-assignment sample + Item 41/42 capstone reports (report first).

1) Kind assignment per source: fish-only / shellfish-only / both; flag wrong-kind
   risk (e.g. shrimp with fish_source and not shellfish_source).
2) Capstone a: seeded-DB invariant design + dry-run counts (true flag → not SAFE).
3) Capstone b: OFF taxonomy ancestry → expected hazard vs missing flag + SAFE.
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
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
from core.knowledge.ingredient_db import get_supabase_config
from core.normalization.normalizer import normalize_ingredient_key
from supabase import create_client

FLAG_TO_RID = {
    "fish_source": "fish_allergy",
    "shellfish_source": "shellfish_allergy",
    "dairy_source": "dairy_free",
    "egg_source": "egg_free",
    "gluten_source": "gluten_free",
    "soy_source": "soy_allergy",
    "sesame_source": "sesame_allergy",
    "peanut_source": "peanut_allergy",
    "tree_nut_source": "tree_nut_allergy",
    "mustard_source": "mustard_allergy",
    "celery_source": "celery_allergy",
    "lupin_source": "lupin_allergy",
    "sulphite_source": "sulfite_sensitive",
}

_SHELLFISH_NAME = re.compile(
    r"\b(prawns?|shrimps?|crabs?|lobsters?|crawfish|crayfish|mussels?|oysters?|"
    r"clams?|scallops?|squids?|octopuses?|octopus|cuttlefish|shellfish|"
    r"molluscs?|mollusks?|crustaceans?)\b",
    re.I,
)

# OFF ancestor ids → expected hazard flags
_HAZARD_ANCESTORS = {
    "en:dairy": "dairy_source",
    "en:milk": "dairy_source",
    "en:cheese": "dairy_source",
    "en:butter": "dairy_source",
    "en:cream": "dairy_source",
    "en:yogurt": "dairy_source",
    "en:whey": "dairy_source",
    "en:filmjolk": "dairy_source",
    "en:egg": "egg_source",
    "en:fish": "fish_source",
    "en:shellfish": "shellfish_source",
    "en:crustacean": "shellfish_source",
    "en:mollusc": "shellfish_source",
    "en:gluten": "gluten_source",
    "en:cereals-containing-gluten": "gluten_source",
    "en:wheat": "gluten_source",
    "en:soy": "soy_source",
    "en:soya": "soy_source",
    "en:sesame": "sesame_source",
    "en:peanut": "peanut_source",
    "en:nuts": "tree_nut_source",
}


def _client():
    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured")
    return create_client(cfg.url, cfg.key)


def _page(c):
    out = []
    start = 0
    while True:
        rows = (
            c.table("ike2_ingredient_groups")
            .select(
                "canonical_name,source,fish_source,shellfish_source,dairy_source,"
                "egg_source,gluten_source,soy_source,sesame_source,peanut_source,"
                "tree_nut_source,mustard_source,celery_source,lupin_source,"
                "sulphite_source,uncertainty_flags,animal_origin,animal_species"
            )
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        out.extend(rows)
        if len(rows) < 1000:
            break
        start += 1000
    return out


def _prod(name: str, rid: str) -> dict:
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
    return {
        "verdict": v,
        "layer": getattr(r, "resolution_layer", None),
        "trusted": bool(getattr(r, "trusted", False)),
        "flags": {
            f: bool(ci.flags.get(f))
            for f in FLAG_TO_RID
            if ci.flags.get(f)
        },
    }


def kind_sample(live: list[dict]) -> dict:
    random.seed(7)
    by_src: dict[str, list] = defaultdict(list)
    for g in live:
        fish = bool(g.get("fish_source"))
        shell = bool(g.get("shellfish_source"))
        if not fish and not shell:
            continue
        if fish and shell:
            kind = "both"
        elif fish:
            kind = "fish_only"
        else:
            kind = "shellfish_only"
        wrong_kind = bool(
            kind == "fish_only" and _SHELLFISH_NAME.search(g["canonical_name"] or "")
        ) and "oyster mushroom" not in (g["canonical_name"] or "").lower()
        by_src[g.get("source") or "?"].append(
            {
                "canonical_name": g["canonical_name"],
                "kind": kind,
                "wrong_kind_risk": wrong_kind,
            }
        )

    out = {}
    for src, rows in sorted(by_src.items()):
        counts = Counter(r["kind"] for r in rows)
        risks = [r for r in rows if r["wrong_kind_risk"]]
        sample = rows[:]
        random.shuffle(sample)
        sample = sample[:40]
        # probe shellfish_allergy on wrong-kind risks (up to 15)
        risk_probes = []
        for r in risks[:15]:
            p = _prod(r["canonical_name"], "shellfish_allergy")
            risk_probes.append(
                {
                    **r,
                    "shellfish_allergy": p["verdict"],
                    "layer": p["layer"],
                    "shellfish_on_ci": bool(p["flags"].get("shellfish_source")),
                    "fish_on_ci": bool(p["flags"].get("fish_source")),
                }
            )
        out[src] = {
            "n": len(rows),
            "kind_counts": dict(counts),
            "wrong_kind_risk_count": len(risks),
            "wrong_kind_risk_names": [r["canonical_name"] for r in risks[:40]],
            "wrong_kind_probes": risk_probes,
            "sample": sample,
        }
    return out


def invariant_dry_run(live: list[dict]) -> dict:
    """Capstone a: for every group × true allergen flag, production must not SAFE."""
    violations = []
    checked = 0
    by_src = Counter()
    # Deduplicate by name (first source wins for probe — production path)
    seen = set()
    for g in live:
        name = g["canonical_name"]
        key = normalize_ingredient_key(name)
        if not key or key in seen:
            continue
        trues = [f for f in FLAG_TO_RID if g.get(f)]
        if not trues:
            continue
        seen.add(key)
        for f in trues:
            rid = FLAG_TO_RID[f]
            checked += 1
            p = _prod(name, rid)
            # Invariant uses compliance-input flag truth after resolve
            if not p["flags"].get(f):
                # layer dropped the live flag — not this invariant's FAIL
                continue
            if p["verdict"] == "SAFE":
                violations.append(
                    {
                        "canonical_name": name,
                        "live_source": g.get("source"),
                        "flag": f,
                        "restriction": rid,
                        "layer": p["layer"],
                        "trusted": p["trusted"],
                    }
                )
                by_src[g.get("source") or "?"] += 1

    return {
        "design": (
            "CI test against seeded DB: for every ike2_ingredient_groups row, "
            "for every allergy/medical restriction whose trigger flag is true on "
            "the compliance input after production resolve, verdict must not be "
            "SAFE (expect NOT_SAFE). This catches Item 34 (KS demotion), Item 42 "
            "(inferred untrusted), and the 26-style table rows when the flag "
            "actually reaches CI."
        ),
        "dry_run_unique_names_with_allergen": len(seen),
        "dry_run_flag_probes": checked,
        "violations": len(violations),
        "violations_by_source": dict(by_src),
        "violation_sample": violations[:40],
        "note": (
            "Dry-run after Item 42 compliance fix. A true CI test should load a "
            "seeded fixture DB, not depend on a developer's local Supabase."
        ),
    }


def _off_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return f"en:{slug}"


def _ancestors(tax: dict, node_id: str, limit: int = 30) -> list[str]:
    out: list[str] = []
    seen = {node_id}
    queue = list((tax.get(node_id) or {}).get("parents") or [])
    while queue and len(out) < limit:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        out.append(cur)
        queue.extend((tax.get(cur) or {}).get("parents") or [])
    return out


def taxonomy_ancestry_scan(live: list[dict]) -> dict:
    tax = json.loads((_BACKEND / "data" / "off_ingredients_taxonomy.json").read_text())
    ont = json.loads((_REPO / "data" / "ontology.json").read_text())
    ont_names = {
        normalize_ingredient_key(r.get("canonical_name") or "")
        for r in ont.get("ingredients") or []
    }
    live_by_name = {}
    for g in live:
        n = normalize_ingredient_key(g.get("canonical_name") or "")
        if n and n not in live_by_name:
            live_by_name[n] = g

    # Index OFF en: nodes by normalized English name
    off_by_norm: dict[str, str] = {}
    for kid, node in tax.items():
        if not kid.startswith("en:"):
            continue
        en_name = ((node.get("name") or {}).get("en") or "").strip()
        if en_name:
            off_by_norm[normalize_ingredient_key(en_name)] = kid
        # also slug of id
        off_by_norm.setdefault(
            normalize_ingredient_key(kid.split(":", 1)[-1].replace("-", " ")), kid
        )

    findings = []
    matched = 0
    for norm in sorted(ont_names | set(live_by_name)):
        off_id = off_by_norm.get(norm) or (
            _off_id(norm) if _off_id(norm) in tax else None
        )
        if not off_id or off_id not in tax:
            continue
        matched += 1
        ancs = _ancestors(tax, off_id)
        expected = {}
        for a in [off_id, *ancs]:
            flag = _HAZARD_ANCESTORS.get(a)
            if flag:
                expected[flag] = a
        if not expected:
            continue
        # flags from L2/live via production CI
        # probe each expected restriction
        for flag, ancestor in expected.items():
            rid = FLAG_TO_RID[flag]
            p = _prod(norm, rid)
            if p["flags"].get(flag):
                continue
            if p["verdict"] != "SAFE":
                continue
            findings.append(
                {
                    "canonical_name": norm,
                    "off_id": off_id,
                    "ancestor": ancestor,
                    "expected_flag": flag,
                    "restriction": rid,
                    "verdict": p["verdict"],
                    "layer": p["layer"],
                    "in_ontology_json": norm in ont_names,
                    "live_source": (live_by_name.get(norm) or {}).get("source"),
                }
            )

    # Priority dairy oat-shape examples
    dairy = [f for f in findings if f["expected_flag"] == "dairy_source"]
    return {
        "off_nodes": len(tax),
        "names_matched_to_off": matched,
        "findings_taxonomy_hazard_flag_false_safe": len(findings),
        "by_flag": dict(Counter(f["expected_flag"] for f in findings)),
        "dairy_oat_shape_count": len(dairy),
        "dairy_sample": dairy[:40],
        "sample": findings[:60],
        "note": (
            "Expected hazards from OFF parent chains (halloumi→cheese→dairy). "
            "Finding = taxonomy says hazard, flag absent on CI, production SAFE. "
            "This catches oat-shape rows invisible to animal_origin/no-kind buckets."
        ),
    }


def main() -> int:
    c = _client()
    live = _page(c)
    print("=== kind sample ===", flush=True)
    kinds = kind_sample(live)
    print(
        json.dumps(
            {
                s: {
                    "n": m["n"],
                    "kind_counts": m["kind_counts"],
                    "wrong_kind_risk_count": m["wrong_kind_risk_count"],
                    "wrong_kind_risk_names": m["wrong_kind_risk_names"][:15],
                    "wrong_kind_probes": m["wrong_kind_probes"][:8],
                }
                for s, m in kinds.items()
            },
            indent=2,
        )
    )

    print("=== invariant dry-run ===", flush=True)
    inv = invariant_dry_run(live)
    print(
        json.dumps(
            {
                k: inv[k]
                for k in (
                    "dry_run_unique_names_with_allergen",
                    "dry_run_flag_probes",
                    "violations",
                    "violations_by_source",
                    "violation_sample",
                    "note",
                )
            },
            indent=2,
        )
    )

    print("=== OFF taxonomy ancestry ===", flush=True)
    tax = taxonomy_ancestry_scan(live)
    print(
        json.dumps(
            {
                k: tax[k]
                for k in (
                    "names_matched_to_off",
                    "findings_taxonomy_hazard_flag_false_safe",
                    "by_flag",
                    "dairy_oat_shape_count",
                    "dairy_sample",
                    "sample",
                    "note",
                )
            },
            indent=2,
        )
    )

    report = {
        "kind_assignment": kinds,
        "capstone_a_invariant": inv,
        "capstone_b_taxonomy": tax,
    }
    out = _REPO / "docs" / "item42_kind_and_capstone.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    md_lines = [
        "# Item 42 — Kind sample + capstone (report)",
        "",
        "## Kind assignment (fish / shellfish / both)",
        "",
    ]
    for src, m in kinds.items():
        md_lines.append(
            f"- **{src}** n={m['n']}: {m['kind_counts']}; "
            f"wrong-kind risk (shellfish-named + fish_only): "
            f"**{m['wrong_kind_risk_count']}**"
        )
        if m["wrong_kind_risk_names"]:
            md_lines.append(
                "  - names: "
                + ", ".join(f"`{n}`" for n in m["wrong_kind_risk_names"][:12])
            )
        for p in m["wrong_kind_probes"][:5]:
            md_lines.append(
                f"  - probe `{p['canonical_name']}` shellfish_allergy="
                f"{p['shellfish_allergy']} via {p['layer']} "
                f"(shellfish_on_ci={p['shellfish_on_ci']}, fish_on_ci={p['fish_on_ci']})"
            )
    md_lines += [
        "",
        "## Capstone a — seeded-DB invariant (design + dry-run)",
        "",
        inv["design"],
        "",
        f"- Unique names with a live allergen true: **{inv['dry_run_unique_names_with_allergen']}**",
        f"- Flag probes (flag reached CI): counted among probes where CI kept the flag",
        f"- Violations (CI flag true → SAFE): **{inv['violations']}** "
        f"{inv['violations_by_source']}",
        f"- {inv['note']}",
        "",
        "## Capstone b — OFF taxonomy ancestry",
        "",
        tax["note"],
        "",
        f"- Names matched to OFF: **{tax['names_matched_to_off']}**",
        f"- Findings (taxonomy hazard, flag false, SAFE): "
        f"**{tax['findings_taxonomy_hazard_flag_false_safe']}** {tax['by_flag']}",
        f"- Dairy oat-shape subset: **{tax['dairy_oat_shape_count']}**",
        "",
    ]
    for f in tax["dairy_sample"][:20]:
        md_lines.append(
            f"- `{f['canonical_name']}` ← `{f['ancestor']}` "
            f"({f['restriction']} SAFE via {f['layer']})"
        )
    md_lines += ["", "Artifact: `docs/item42_kind_and_capstone.json`."]
    md = _REPO / "docs" / "item42_kind_and_capstone.md"
    md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("Wrote", out, md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
