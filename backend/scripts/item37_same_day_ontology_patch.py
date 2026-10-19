#!/usr/bin/env python3
"""Same-day: patch ontology.json false-SAFEs; report before/after + all 44 drifts."""
from __future__ import annotations

import json
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
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology as lo
from core.knowledge.ike2.verdict import to_external
from core.knowledge.ingredient_db import get_supabase_config
from core.normalization.normalizer import normalize_ingredient_key
from supabase import create_client

ONT_PATH = _REPO / "data" / "ontology.json"

VERDICT_RELEVANT = (
    "animal_origin",
    "fish_source",
    "shellfish_source",
    "dairy_source",
    "egg_source",
    "gluten_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
    "insect_derived",
    "bee_product",
    "fungal",
    "enzyme_animal_source",
)

# Patches: name -> flags to force true (+ plant_origin false when animal)
PATCHES: dict[str, dict] = {
    "oyster": {
        "animal_origin": True,
        "shellfish_source": True,
        "fish_source": False,
        "plant_origin": False,
        "animal_species": "shellfish",
    },
    "mussel": {
        "animal_origin": True,
        "shellfish_source": True,
        "fish_source": False,
        "plant_origin": False,
        "animal_species": "shellfish",
    },
    "scallop": {
        "animal_origin": True,
        "shellfish_source": True,
        "fish_source": False,
        "plant_origin": False,
        "animal_species": "shellfish",
    },
    "cuttlefish": {
        "animal_origin": True,
        "shellfish_source": True,
        "fish_source": False,
        "plant_origin": False,
        "animal_species": "shellfish",
    },
    "caviar": {
        "animal_origin": True,
        "fish_source": True,
        "shellfish_source": False,
        "plant_origin": False,
        "animal_species": "fish",
    },
    "dulce de leche": {
        "animal_origin": True,
        "dairy_source": True,
        "egg_source": True,
        "plant_origin": False,
    },
    "halloumi": {
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
    },
    "filmjölk": {
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
    },
    "viili": {
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
    },
    "goat milk fat": {
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
    },
}

LOCUST_NEW = {
    "canonical_name": "locust",
    "id": "locust",
    "aliases": ["locusts"],
    "animal_origin": True,
    "insect_derived": True,
    "plant_origin": False,
    "knowledge_state": "AUTO_CLASSIFIED",
    "asserted_flags": ["animal_origin", "insect_derived"],
}

PROBES = [
    ("oyster", "shellfish_allergy"),
    ("mussel", "shellfish_allergy"),
    ("scallop", "shellfish_allergy"),
    ("cuttlefish", "shellfish_allergy"),
    ("cuttlefish", "vegan"),
    ("caviar", "fish_allergy"),
    ("caviar", "vegan"),
    ("dulce de leche", "egg_free"),
    ("dulce de leche", "dairy_free"),
    ("halloumi", "dairy_free"),
    ("filmjölk", "dairy_free"),
    ("viili", "dairy_free"),
    ("goat milk fat", "dairy_free"),
    ("locust", "vegan"),
    ("locust", "no_insect_derived"),
]


def _client():
    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured")
    return create_client(cfg.url, cfg.key)


def _page(c, **filters):
    out = []
    start = 0
    while True:
        q = c.table("ike2_ingredient_groups").select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        rows = q.range(start, start + 999).execute().data or []
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
        "canonical_name": name,
        "restriction": rid,
        "verdict": v,
        "layer": getattr(r, "resolution_layer", None),
        "trusted": bool(getattr(r, "trusted", False)),
        "hazards": {
            f: bool(ci.flags.get(f))
            for f in (
                "animal_origin",
                "fish_source",
                "shellfish_source",
                "dairy_source",
                "egg_source",
                "insect_derived",
            )
            if ci.flags.get(f)
        },
    }


def _asserted_for(row: dict) -> list[str]:
    asserted = set()
    for f in BOOL_FLAGS:
        if row.get(f) is True:
            asserted.add(f)
    # keep prior asserted that are still true
    for f in row.get("asserted_flags") or []:
        if row.get(f) is True:
            asserted.add(f)
    return sorted(asserted)


def list_drifts(c) -> list[dict]:
    ont_raw = json.loads(ONT_PATH.read_text())
    by_name = {}
    for r in ont_raw["ingredients"]:
        n = normalize_ingredient_key(r.get("canonical_name") or "")
        if n:
            by_name[n] = r
    out = []
    for g in _page(c, source="ontology"):
        name = normalize_ingredient_key(g.get("canonical_name") or "")
        if not name or name not in by_name:
            continue
        mapped, _ = map_record(
            by_name[name], "ontology", default_knowledge_state("ontology")
        )
        diffs = []
        for f in BOOL_FLAGS:
            lv, ov = bool(g.get(f)), bool(mapped.get(f))
            if lv != ov:
                diffs.append(
                    {
                        "flag": f,
                        "direction": "live_true_l2_false" if lv and not ov else "live_false_l2_true",
                        "live": lv,
                        "l2": ov,
                    }
                )
        ls = (g.get("animal_species") or "") or ""
        os_ = (mapped.get("animal_species") or "") or ""
        if str(ls).lower() != str(os_).lower() and (ls or os_):
            diffs.append(
                {
                    "flag": "animal_species",
                    "direction": "species_mismatch",
                    "live": ls,
                    "l2": os_,
                }
            )
        vdiffs = [
            d
            for d in diffs
            if d["flag"] in VERDICT_RELEVANT or d["flag"] == "animal_species"
        ]
        if vdiffs:
            out.append(
                {
                    "canonical_name": g["canonical_name"],
                    "knowledge_state": g.get("knowledge_state"),
                    "diffs": vdiffs,
                }
            )
    out.sort(key=lambda r: r["canonical_name"])
    return out


def apply_patches() -> dict:
    data = json.loads(ONT_PATH.read_text())
    by_key = {
        normalize_ingredient_key(r.get("canonical_name") or ""): r
        for r in data["ingredients"]
    }
    changed = []
    for name, flags in PATCHES.items():
        key = normalize_ingredient_key(name)
        row = by_key.get(key)
        if not row:
            raise SystemExit(f"missing ontology row: {name}")
        before = {k: row.get(k) for k in flags}
        for k, v in flags.items():
            row[k] = v
        row["asserted_flags"] = _asserted_for(row)
        # drop plant from asserted if animal
        if row.get("animal_origin") and row.get("plant_origin"):
            row["plant_origin"] = False
            row["asserted_flags"] = _asserted_for(row)
        changed.append(
            {
                "canonical_name": row["canonical_name"],
                "before": before,
                "after": {k: row.get(k) for k in flags},
                "asserted_flags": row["asserted_flags"],
            }
        )

    if normalize_ingredient_key("locust") not in by_key:
        data["ingredients"].append(dict(LOCUST_NEW))
        changed.append(
            {
                "canonical_name": "locust",
                "before": None,
                "after": LOCUST_NEW,
                "asserted_flags": LOCUST_NEW["asserted_flags"],
                "added": True,
            }
        )
    else:
        row = by_key[normalize_ingredient_key("locust")]
        for k, v in LOCUST_NEW.items():
            if k in ("canonical_name", "id", "aliases"):
                continue
            row[k] = v
        row["asserted_flags"] = _asserted_for(row)
        changed.append(
            {
                "canonical_name": "locust",
                "before": "existed",
                "after": {k: row.get(k) for k in ("animal_origin", "insect_derived")},
                "asserted_flags": row["asserted_flags"],
            }
        )

    ONT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    lo.reset_cache()
    cache.clear()
    return {"patched": changed, "n_ingredients": len(data["ingredients"])}


def main() -> int:
    c = _client()
    before_drifts = list_drifts(c)
    before_probes = [_prod(n, r) for n, r in PROBES]

    patch_meta = apply_patches()

    after_probes = [_prod(n, r) for n, r in PROBES]
    after_drifts = list_drifts(c)

    # by-flag summary of the 44
    by_flag_dir = Counter()
    for d in before_drifts:
        for x in d["diffs"]:
            by_flag_dir[f"{x['flag']}:{x['direction']}"] += 1

    report = {
        "note": (
            "animal_origin live_true/l2_false drifts were only caviar + cuttlefish "
            "(already in the seafood patch list). oyster/mussel/scallop already "
            "NOT_SAFE via L1_truth_anchor before the file patch; L2 hygiene still applied."
        ),
        "before_drift_count": len(before_drifts),
        "after_drift_count": len(after_drifts),
        "by_flag_direction_before": dict(by_flag_dir),
        "all_44_drifts_before": before_drifts,
        "remaining_verdict_drifts_after": after_drifts,
        "patch": patch_meta,
        "probes_before": before_probes,
        "probes_after": after_probes,
        "probe_deltas": [
            {
                "canonical_name": a["canonical_name"],
                "restriction": a["restriction"],
                "before": b["verdict"],
                "after": a["verdict"],
                "before_layer": b["layer"],
                "after_layer": a["layer"],
                "changed": b["verdict"] != a["verdict"] or b["layer"] != a["layer"],
            }
            for b, a in zip(before_probes, after_probes)
        ],
    }

    out = _REPO / "docs" / "item37_same_day_ontology_patch.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    # markdown
    lines = [
        "# Item 37 — Same-day ontology.json false-SAFE patches",
        "",
        report["note"],
        "",
        "## Production probes (before → after)",
        "",
        "| Name | Restriction | Before | After | Before layer | After layer |",
        "|------|-------------|--------|-------|--------------|-------------|",
    ]
    for d in report["probe_deltas"]:
        mark = " **" if d["changed"] else ""
        lines.append(
            f"| `{d['canonical_name']}` | `{d['restriction']}` | {d['before']} | "
            f"{d['after']}{mark} | {d['before_layer']} | {d['after_layer']} |"
        )
    lines += [
        "",
        f"## All {len(before_drifts)} verdict-relevant drifts (before patch)",
        "",
        "By flag × direction:",
        "",
    ]
    for k, n in sorted(by_flag_dir.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- `{k}`: {n}")
    lines += ["", "### Named rows", ""]
    for d in before_drifts:
        parts = [
            f"{x['flag']} ({x['direction']}: live={x['live']!r} l2={x['l2']!r})"
            for x in d["diffs"]
        ]
        lines.append(f"- `{d['canonical_name']}` — {'; '.join(parts)}")
    lines += [
        "",
        f"## Remaining verdict-relevant drifts after patch: **{len(after_drifts)}**",
        "",
        "Artifact: `docs/item37_same_day_ontology_patch.json`.",
    ]
    md = _REPO / "docs" / "item37_same_day_ontology_patch.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"before_drifts": len(before_drifts), "after_drifts": len(after_drifts),
                      "deltas": [d for d in report["probe_deltas"] if d["changed"]],
                      "wrote": [str(out), str(md)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
