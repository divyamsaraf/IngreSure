#!/usr/bin/env python3
"""Item 37 ops: IFCT fish re-inject, animal/no-kind report, ortho review,
DISCOVERED restore (dairy trio + Phase-1 synthetic demotions).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS
from core.knowledge.ike2.etl.bulk_inject import _CollectWriter, inject, load_dump, main as bulk_main
from core.knowledge.ike2.etl.reconcile import reconcile
from core.knowledge.ike2.orthographic_variants import (
    ORTHO_RESTRICTIONS,
    generate_orthographic_pairs,
)
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.knowledge.ingredient_db import get_supabase_config
from core.normalization.normalizer import normalize_ingredient_key
from supabase import create_client

KIND_FLAGS = (
    "fish_source",
    "shellfish_source",
    "dairy_source",
    "egg_source",
    "insect_derived",
    "bee_product",
)
SPECIES_ALLERGY = {
    "fish_allergy": ("fish_source", "animal_species"),
    "shellfish_allergy": ("shellfish_source", "animal_species"),
    "egg_free": ("egg_source",),
    "dairy_free": ("dairy_source",),
}


def _client():
    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured")
    return create_client(cfg.url, cfg.key)


def _page_groups(c, **filters):
    out = []
    start = 0
    page = 1000
    while True:
        q = c.table("ike2_ingredient_groups").select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        rows = q.range(start, start + page - 1).execute().data or []
        out.extend(rows)
        if len(rows) < page:
            break
        start += page
    return out


def _verdict(name: str, restriction: str) -> str:
    r = resolve(name, None)
    ci = to_compliance_input(r, query_atom=name)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={restriction: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


def _flags_snapshot(name: str) -> dict:
    r = resolve(name, None)
    g = r.group
    if g is None:
        return {"resolved": False}
    if hasattr(g, "flags"):
        flags = dict(g.flags)
        canon = g.canonical_name
        ks = g.knowledge_state
        species = flags.get("animal_species")
    else:
        flags = dict(vars(g))
        canon = getattr(g, "canonical_name", "")
        ks = getattr(g, "knowledge_state", None)
        species = getattr(g, "animal_species", None)
    return {
        "resolved": True,
        "canonical_name": canon,
        "knowledge_state": ks,
        "animal_origin": bool(flags.get("animal_origin")),
        "fish_source": bool(flags.get("fish_source")),
        "shellfish_source": bool(flags.get("shellfish_source")),
        "dairy_source": bool(flags.get("dairy_source")),
        "egg_source": bool(flags.get("egg_source")),
        "insect_derived": bool(flags.get("insect_derived")),
        "bee_product": bool(flags.get("bee_product")),
        "animal_species": species,
        "source": flags.get("source") or getattr(g, "source", None),
    }


def _ifct_fish_chapter_names() -> set[str]:
    rows = json.loads((_REPO / "data" / "layer1_ifct.json").read_text())
    names = set()
    for r in rows:
        if r.get("fish_source") or r.get("shellfish_source"):
            names.add(normalize_ingredient_key(r["canonical_name"]))
    return names


def count_ifct_underflag(c) -> dict:
    chapter = _ifct_fish_chapter_names()
    live = _page_groups(c, source="ifct")
    under = []
    for g in live:
        name = normalize_ingredient_key(g.get("canonical_name") or "")
        if name not in chapter:
            # also include *fish/prawn/crab compounds on live IFCT even if dump key drifted
            nl = name
            if not re.search(
                r"(fish|prawn|shrimp|crab|lobster|squid|clam|oyster|mussel)\b", nl
            ):
                continue
            if "oyster mushroom" in nl:
                continue
        if g.get("fish_source") or g.get("shellfish_source"):
            continue
        if name not in chapter and not re.search(
            r"(fish|prawn|shrimp|crab|lobster|squid|clam|oyster|mussel)\b", name
        ):
            continue
        vf = _verdict(g["canonical_name"], "fish_allergy")
        vs = _verdict(g["canonical_name"], "shellfish_allergy")
        under.append(
            {
                "canonical_name": g["canonical_name"],
                "animal_origin": g.get("animal_origin"),
                "fish_source": g.get("fish_source"),
                "shellfish_source": g.get("shellfish_source"),
                "fish_allergy": vf,
                "shellfish_allergy": vs,
            }
        )
    # Prefer chapter-name intersection for the primary count
    chapter_live = [
        g
        for g in live
        if normalize_ingredient_key(g.get("canonical_name") or "") in chapter
    ]
    chapter_under = [
        u
        for u in under
        if normalize_ingredient_key(u["canonical_name"]) in chapter
    ]
    vc = Counter(f"{u['fish_allergy']}/{u['shellfish_allergy']}" for u in chapter_under)
    return {
        "ifct_live_total": len(live),
        "ifct_fish_chapter_live": len(chapter_live),
        "ifct_fish_chapter_underflagged": len(chapter_under),
        "underflagged_names": [u["canonical_name"] for u in chapter_under],
        "underflagged_detail": chapter_under,
        "underflagged_verdict_counts": dict(vc),
        "fish_source_true_live_ifct": sum(1 for g in live if g.get("fish_source")),
        "shellfish_source_true_live_ifct": sum(1 for g in live if g.get("shellfish_source")),
    }


def seed_writer_from_rows(rows) -> _CollectWriter:
    w = _CollectWriter()
    for r in rows:
        name = normalize_ingredient_key(r.get("canonical_name") or "")
        if not name:
            continue
        payload = {f: bool(r.get(f)) for f in BOOL_FLAGS}
        payload.update(
            {
                "canonical_name": name,
                "knowledge_state": r.get("knowledge_state") or "AUTO_CLASSIFIED",
                "source": r.get("source") or "ontology",
                "asserted_flags": list(r.get("asserted_flags") or []),
                "animal_species": r.get("animal_species"),
                "uncertainty_flags": list(r.get("uncertainty_flags") or []),
            }
        )
        w.insert_group(payload)
    return w


def dry_run_ifct(seed_rows, label: str) -> dict:
    _, records = load_dump(str(_REPO / "data" / "layer1_ifct.json"))
    # normalize dump names for matching
    for r in records:
        r["canonical_name"] = normalize_ingredient_key(r.get("canonical_name") or "")
    w = seed_writer_from_rows(seed_rows)
    before_disc = w.list_discovered_names()
    stats = inject(records, "ifct", w)
    demoted = []
    for name, g in w.groups.items():
        if g.get("knowledge_state") == "DISCOVERED" and name not in before_disc:
            demoted.append(name)
    # also count needs_review from stats
    return {
        "label": label,
        "seeded": len(seed_rows),
        "stats": stats.as_dict(),
        "new_discovered": sorted(demoted),
        "needs_review": stats.needs_review,
    }


def animal_no_kind_report(c) -> dict:
    live = _page_groups(c)
    no_kind = [
        g
        for g in live
        if g.get("animal_origin") and not any(g.get(f) for f in KIND_FLAGS)
    ]
    infoods = [
        g
        for g in live
        if g.get("source") == "infoods"
        and (g.get("fish_source") or g.get("shellfish_source"))
    ]
    # index infoods by alias via ingredients/aliases is heavy; use name + scientific-ish
    infoods_keys: dict[str, str] = {}
    for g in infoods:
        canon = normalize_ingredient_key(g.get("canonical_name") or "")
        infoods_keys[canon] = g["canonical_name"]
        # animal_species sometimes holds a latin name
        sp = normalize_ingredient_key(str(g.get("animal_species") or ""))
        if sp:
            infoods_keys[sp] = g["canonical_name"]

    # Pull aliases for infoods fish groups (best-effort)
    for g in infoods:
        ings = (
            c.table("ike2_ingredients")
            .select("id,normalized_name")
            .eq("group_id", g["id"])
            .execute()
            .data
            or []
        )
        for ing in ings:
            infoods_keys[normalize_ingredient_key(ing.get("normalized_name") or "")] = g[
                "canonical_name"
            ]
            als = (
                c.table("ike2_aliases")
                .select("normalized_alias")
                .eq("ingredient_id", ing["id"])
                .execute()
                .data
                or []
            )
            for a in als:
                infoods_keys[normalize_ingredient_key(a.get("normalized_alias") or "")] = g[
                    "canonical_name"
                ]

    matched = []
    unmatched = []
    for g in no_kind:
        key = normalize_ingredient_key(g.get("canonical_name") or "")
        hit = infoods_keys.get(key)
        if hit:
            matched.append(
                {
                    "live": g["canonical_name"],
                    "source": g.get("source"),
                    "infoods": hit,
                }
            )
        else:
            unmatched.append(
                {
                    "canonical_name": g["canonical_name"],
                    "source": g.get("source"),
                }
            )
    by_src = Counter(g.get("source") or "?" for g in no_kind)
    return {
        "animal_no_kind": len(no_kind),
        "animal_no_kind_by_source": dict(by_src),
        "no_kind_matched_infoods": matched,
        "no_kind_unmatched_count": len(unmatched),
        "no_kind_unmatched_sample": unmatched[:120],
        "no_kind_unmatched_names": [u["canonical_name"] for u in unmatched],
        "note": "Report only — no flips applied.",
    }


def rewrite_ortho_allergy_review() -> dict:
    findings = []
    ok_rows = []
    for left, right, kind in generate_orthographic_pairs():
        for rid in ORTHO_RESTRICTIONS:
            vl = _verdict(left, rid)
            vr = _verdict(right, rid)
            if {vl, vr} != {"SAFE", "UNCERTAIN"}:
                continue
            safe_name = left if vl == "SAFE" else right
            uncertain_name = right if vl == "SAFE" else left
            snap = _flags_snapshot(safe_name)
            animalish = bool(
                snap.get("animal_origin")
                or snap.get("fish_source")
                or snap.get("shellfish_source")
                or snap.get("egg_source")
                or snap.get("dairy_source")
                or snap.get("insect_derived")
                or snap.get("bee_product")
            )
            species_hit = False
            if rid in SPECIES_ALLERGY:
                for key in SPECIES_ALLERGY[rid]:
                    if key == "animal_species":
                        sp = str(snap.get("animal_species") or "").lower()
                        if rid == "fish_allergy" and (
                            sp == "fish" or sp.startswith("fish")
                        ):
                            species_hit = True
                        if rid == "shellfish_allergy" and (
                            "shellfish" in sp or sp in ("shrimp", "crab", "lobster")
                        ):
                            species_hit = True
                    elif snap.get(key):
                        species_hit = True
            # Finding: SAFE under a species-allergen restriction while that
            # species flag (or matching animal_species) is present on the SAFE side.
            # Fish SAFE under shellfish_allergy is OK (cross-species).
            is_finding = False
            reason = ""
            if snap.get("resolved") and rid == "fish_allergy":
                if snap.get("fish_source") or str(snap.get("animal_species") or "").lower() in (
                    "fish",
                ) or str(snap.get("animal_species") or "").lower().startswith("fish"):
                    is_finding = True
                    reason = (
                        "FINDING: SAFE under fish_allergy with fish identity; "
                        f"flags={ {k: snap.get(k) for k in ('animal_origin','fish_source','shellfish_source','animal_species','source')} }"
                    )
                elif snap.get("animal_origin") and not any(
                    snap.get(f)
                    for f in (
                        "shellfish_source",
                        "dairy_source",
                        "egg_source",
                        "insect_derived",
                        "bee_product",
                    )
                ):
                    # animal with no kind — possible underflagged fish (snapper etc.)
                    is_finding = True
                    reason = (
                        "FINDING: SAFE under fish_allergy with animal_origin and no kind flag; "
                        f"flags={ {k: snap.get(k) for k in ('animal_origin','fish_source','shellfish_source','animal_species','source')} }"
                    )
            elif snap.get("resolved") and rid == "shellfish_allergy":
                if snap.get("shellfish_source") or "shellfish" in str(
                    snap.get("animal_species") or ""
                ).lower():
                    is_finding = True
                    reason = (
                        "FINDING: SAFE under shellfish_allergy with shellfish identity; "
                        f"flags={ {k: snap.get(k) for k in ('animal_origin','fish_source','shellfish_source','animal_species','source')} }"
                    )
            elif snap.get("resolved") and species_hit and rid in (
                "egg_free",
                "dairy_free",
                "peanut_allergy",
                "tree_nut_allergy",
                "soy_allergy",
                "sesame_allergy",
                "mustard_allergy",
                "celery_allergy",
                "lupin_allergy",
            ):
                is_finding = True
                reason = (
                    f"FINDING: SAFE-side carries matching allergen flag under {rid}; "
                    f"flags={snap}"
                )
            if not reason:
                reason = (
                    f"COMPUTED_OK: SAFE-side flags animal_origin={snap.get('animal_origin')} "
                    f"fish={snap.get('fish_source')} shellfish={snap.get('shellfish_source')} "
                    f"species={snap.get('animal_species')} source={snap.get('source')}"
                )
            row = {
                "kind": kind,
                "restriction": rid,
                "safe": safe_name,
                "uncertain": uncertain_name,
                "safe_flags": snap,
                "reason": reason,
                "finding": is_finding,
            }
            if is_finding:
                findings.append(row)
            ok_rows.append(row)
    out_path = _REPO / "docs" / "item37_ortho_allergy_safe_side_review.json"
    out_path.write_text(json.dumps(ok_rows, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "pairs_reviewed": len(ok_rows),
        "findings": len(findings),
        "finding_names": sorted({f["safe"] for f in findings}),
        "finding_sample": findings[:20],
    }


def _phase1_names() -> list[str]:
    md = (_REPO / "docs" / "item11_phase1_flag_changes.md").read_text()
    names = []
    for m in re.finditer(r"^- `([^`]+)` —", md, re.M):
        names.append(normalize_ingredient_key(m.group(1)))
    return sorted(set(names))


def build_restore_dump() -> Path:
    """Dairy-trio KS restore only.

    Phase-1 synthetic demotions use the minimal form (KS→AUTO, dump synthetic
    left unasserted) — see ``item37_synthetic_nokind_adapt_followup.py``. Do not
    blanket-assert synthetic=false.
    """
    dairy_trio = [
        "cultured buttermilk",
        "flavoured milks",
        "traditional buttermilk (churning)",
    ]
    records = []
    for name in dairy_trio:
        records.append(
            {
                "canonical_name": name,
                "dairy_source": True,
                "animal_origin": True,
                "asserted_flags": ["dairy_source", "animal_origin"],
                "knowledge_state": "AUTO_CLASSIFIED",
            }
        )
    path = _REPO / "data" / "layer1_phase1_discovered_restore.json"
    path.write_text(
        json.dumps({"source": "ontology", "ingredients": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    c = _client()
    report: dict = {"steps": {}}

    print("=== 1a BEFORE IFCT underflag ===", flush=True)
    before = count_ifct_underflag(c)
    report["steps"]["1a_before"] = before
    print(json.dumps({k: before[k] for k in before if k != "underflagged_detail"}, indent=2))

    print("=== 1b ontology-seeded dry-run ===", flush=True)
    ont = json.loads((_REPO / "data" / "ontology.json").read_text())
    ont_rows = ont.get("ingredients") or []
    # normalize
    for r in ont_rows:
        r["canonical_name"] = normalize_ingredient_key(r.get("canonical_name") or "")
        r.setdefault("knowledge_state", "AUTO_CLASSIFIED")
        r.setdefault("source", "ontology")
        # true-only asserted for seed
        r["asserted_flags"] = [f for f in BOOL_FLAGS if r.get(f)]
    ont_dry = dry_run_ifct(ont_rows, "ontology-seeded")
    report["steps"]["1b_ontology_dry_run"] = ont_dry
    print(json.dumps(ont_dry, indent=2))

    print("=== 1b live-seeded dry-run ===", flush=True)
    live_all = _page_groups(c)
    live_dry = dry_run_ifct(live_all, "live-seeded")
    report["steps"]["1b_live_dry_run"] = live_dry
    print(json.dumps(live_dry, indent=2))

    if ont_dry["needs_review"] != 0 or live_dry["needs_review"] != 0:
        print("ABORT: demotions in dry-run", file=sys.stderr)
        (_REPO / "docs" / "item37_fish_negation_discovered_ops.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        return 1

    print("=== 1b live IFCT inject ===", flush=True)
    rc = bulk_main(
        [
            str(_REPO / "data" / "layer1_ifct.json"),
            "--source",
            "ifct",
            "--discovered-diff",
            str(_REPO / "docs" / "item37_ifct_inject_discovered_diff.json"),
        ]
    )
    report["steps"]["1b_live_inject_rc"] = rc
    if rc != 0:
        print("IFCT inject failed (possibly unexplained DISCOVERED)", file=sys.stderr)

    print("=== 1b AFTER recount ===", flush=True)
    after = count_ifct_underflag(c)
    report["steps"]["1b_after"] = after
    print(json.dumps({k: after[k] for k in after if k != "underflagged_detail"}, indent=2))

    print("=== 1c animal no-kind (no flip) ===", flush=True)
    nokind = animal_no_kind_report(c)
    report["steps"]["1c"] = {
        k: nokind[k]
        for k in nokind
        if k not in ("no_kind_unmatched_names",)
    }
    report["steps"]["1c"]["no_kind_unmatched_names_path"] = str(
        _REPO / "docs" / "item37_animal_no_kind_unmatched.json"
    )
    (_REPO / "docs" / "item37_animal_no_kind_unmatched.json").write_text(
        json.dumps(nokind["no_kind_unmatched_names"], indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "animal_no_kind": nokind["animal_no_kind"],
                "by_source": nokind["animal_no_kind_by_source"],
                "matched_infoods": len(nokind["no_kind_matched_infoods"]),
                "unmatched": nokind["no_kind_unmatched_count"],
                "matched_sample": nokind["no_kind_matched_infoods"][:20],
            },
            indent=2,
        )
    )

    print("=== 1d ortho computed review ===", flush=True)
    ortho = rewrite_ortho_allergy_review()
    report["steps"]["1d_ortho"] = ortho
    print(json.dumps({k: ortho[k] for k in ortho if k != "finding_sample"}, indent=2))

    print("=== 3 restore dump + inject ===", flush=True)
    restore_path = build_restore_dump()
    report["steps"]["3_restore_dump"] = str(restore_path)
    report["steps"]["3_phase1_count"] = len(_phase1_names())
    report["steps"]["3_dairy_trio"] = [
        "cultured buttermilk",
        "flavoured milks",
        "traditional buttermilk (churning)",
    ]
    report["steps"]["3_dairy_demotion_cause"] = (
        "asserted dairy_source false→true during stem/family inject "
        "(dairy was asserted false from prior full-block pollution or deliberate "
        "negative); reconcile demoted KS to DISCOVERED. dairy_source=true is correct "
        "for these buttermilk/milk rows — restore KS to AUTO_CLASSIFIED only."
    )
    rc2 = bulk_main(
        [
            str(restore_path),
            "--source",
            "ontology",
            "--curated-asserted-negatives",
            "--discovered-diff",
            str(_REPO / "docs" / "item37_phase1_restore_discovered_diff.json"),
        ]
    )
    report["steps"]["3_restore_inject_rc"] = rc2

    # DISCOVERED after
    disc = _page_groups(c, knowledge_state="DISCOVERED")
    report["steps"]["3_discovered_after"] = {
        "count": len(disc),
        "names": sorted(g["canonical_name"] for g in disc),
    }
    print("DISCOVERED after restore:", len(disc))

    out = _REPO / "docs" / "item37_fish_negation_discovered_ops.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Wrote", out)
    return 0 if rc == 0 and rc2 == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
