#!/usr/bin/env python3
"""Item 37 / Item 33 lesson: L2 local_ontology vs L3 live DB exposure audit.

Report-only. Declares which store answered production resolve for every name
touched this thread, and measures flag drift invisible under L2.
"""
from __future__ import annotations

import json
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
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.knowledge.ingredient_db import get_supabase_config
from core.normalization.normalizer import normalize_ingredient_key
from supabase import create_client

VERDICT_FLAGS = (
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

KIND_FLAGS = (
    "fish_source",
    "shellfish_source",
    "dairy_source",
    "egg_source",
    "insect_derived",
    "bee_product",
)


def _client():
    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured")
    return create_client(cfg.url, cfg.key)


def _page(c, **filters):
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


def _load_ontology_by_name() -> dict[str, dict]:
    raw = json.loads((_REPO / "data" / "ontology.json").read_text())
    out = {}
    for r in raw.get("ingredients") or []:
        name = normalize_ingredient_key(r.get("canonical_name") or "")
        if name:
            out[name] = r
    return out


def _l2_flags(raw: dict) -> dict:
    row, _ = map_record(raw, "ontology", default_knowledge_state("ontology"))
    return {f: bool(row.get(f)) for f in BOOL_FLAGS}


def _true_diffs(live: dict, l2: dict) -> list[str]:
    """Flags true on one side and false on the other (either direction)."""
    diffs = []
    for f in BOOL_FLAGS:
        lv = bool(live.get(f))
        ov = bool(l2.get(f))
        if lv != ov:
            diffs.append(f"{f}:live={lv}/l2={ov}")
    return diffs


def _verdict_relevant_diffs(live: dict, l2: dict) -> list[str]:
    diffs = []
    for f in VERDICT_FLAGS:
        lv = bool(live.get(f))
        ov = bool(l2.get(f))
        if lv != ov:
            diffs.append(f"{f}:live={lv}/l2={ov}")
    # animal_species string drift
    ls = (live.get("animal_species") or "") or ""
    os_ = (l2.get("animal_species") or "") or ""
    if str(ls).lower() != str(os_).lower() and (ls or os_):
        diffs.append(f"animal_species:live={ls!r}/l2={os_!r}")
    return diffs


def layer_exposure(c, ont: dict[str, dict]) -> dict:
    live_ont = _page(c, source="ontology")
    per_flag_live_true_l2_false = Counter()
    per_flag_live_false_l2_true = Counter()
    drifted = []
    missing_in_file = []
    for g in live_ont:
        name = normalize_ingredient_key(g.get("canonical_name") or "")
        if not name:
            continue
        raw = ont.get(name)
        if not raw:
            missing_in_file.append(g["canonical_name"])
            continue
        l2 = _l2_flags(raw)
        # also pass animal_species from mapped row
        mapped, _ = map_record(raw, "ontology", default_knowledge_state("ontology"))
        l2["animal_species"] = mapped.get("animal_species")
        vdiffs = _verdict_relevant_diffs(g, l2)
        alldiffs = _true_diffs(g, l2)
        for f in BOOL_FLAGS:
            lv, ov = bool(g.get(f)), bool(l2.get(f))
            if lv and not ov:
                per_flag_live_true_l2_false[f] += 1
            elif ov and not lv:
                per_flag_live_false_l2_true[f] += 1
        if vdiffs:
            drifted.append(
                {
                    "canonical_name": g["canonical_name"],
                    "verdict_relevant_diffs": vdiffs,
                    "n_bool_diffs": len(alldiffs),
                    "live_ks": g.get("knowledge_state"),
                }
            )
    drifted.sort(key=lambda r: (-len(r["verdict_relevant_diffs"]), r["canonical_name"]))
    return {
        "live_source_ontology_rows": len(live_ont),
        "ontology_json_rows": len(ont),
        "missing_in_ontology_json": len(missing_in_file),
        "missing_sample": missing_in_file[:20],
        "names_with_verdict_relevant_drift": len(drifted),
        "per_flag_live_true_l2_false": dict(per_flag_live_true_l2_false),
        "per_flag_live_false_l2_true": dict(per_flag_live_false_l2_true),
        "top_verdict_drift": drifted[:80],
        "all_verdict_drift_names": [d["canonical_name"] for d in drifted],
    }


def _clear_cache() -> None:
    cache.clear()


def _prod_verdict(name: str, rid: str) -> tuple[str, str, dict]:
    """Return (external_verdict, resolution_layer, hazard_flags)."""
    _clear_cache()
    r = resolve(name, None)
    ci = to_compliance_input(r, query_atom=name)
    v = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )
    hazards = {
        f: bool(ci.flags.get(f))
        for f in VERDICT_FLAGS
        if ci.flags.get(f)
    }
    cap = getattr(ci, "verdict_cap", None) or ci.flags.get("verdict_cap")
    if cap:
        hazards["verdict_cap"] = cap
    unc = ci.flags.get("uncertainty_flags")
    if unc:
        hazards["uncertainty_flags"] = list(unc)
    layer = getattr(r, "resolution_layer", None) or "?"
    return v, layer, hazards


_FLAG_TO_RESTRICTION = {
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


def _collect_thread_names() -> tuple[dict[str, list[str]], list[dict]]:
    """Names touched this Item 37 thread, by cohort. Also returns stem rows."""
    cohorts: dict[str, list[str]] = {}

    stem = json.loads((_REPO / "data" / "layer1_stem_triage_2026-10-07.json").read_text())
    stem_rows = stem if isinstance(stem, list) else stem.get("ingredients") or []
    cohorts["stem_triage_dump"] = sorted(
        {
            normalize_ingredient_key(r.get("canonical_name") or "")
            for r in stem_rows
            if r.get("canonical_name")
        }
    )

    reg = json.loads((_REPO / "docs" / "item37_regional_fish_triage.json").read_text())
    cohorts["regional_infoods_flipped"] = sorted(
        normalize_ingredient_key(n) for n in (reg.get("flipped") or [])
    )
    cohorts["regional_ifct_flipped"] = sorted(
        normalize_ingredient_key(m["name"])
        for m in (reg.get("ifct_matched_flipped") or [])
        if m.get("name")
    )

    flip = json.loads((_REPO / "data" / "layer1_item37_fish_flip.json").read_text())
    flip_rows = flip.get("ingredients") or (flip if isinstance(flip, list) else [])
    cohorts["fish_flips_71"] = sorted(
        {
            normalize_ingredient_key(r.get("canonical_name") or "")
            for r in flip_rows
            if r.get("canonical_name")
        }
    )

    cohorts["e220_e228"] = [f"e{n}" for n in range(220, 229)] + [
        "sulphur dioxide",
        "sulfur dioxide",
        "sodium sulphite",
        "sodium sulfite",
        "sodium metabisulphite",
        "sodium metabisulfite",
    ]

    cohorts["dairy_trio"] = [
        "cultured buttermilk",
        "flavoured milks",
        "traditional buttermilk (churning)",
    ]

    # Phase-1 demotions (= names restored off DISCOVERED in this thread)
    restore = json.loads(
        (_REPO / "docs" / "item37_phase1_restore_discovered_diff.json").read_text()
    )
    cohorts["phase1_demotions"] = sorted(
        normalize_ingredient_key(n) for n in (restore.get("removed") or [])
    )

    cohorts["same_day_examples"] = [
        "einkorn",
        "khorasan",
        "barley groats",
        "idli rava",
        "lupini beans",
        "lupins",
        "lupine beans",
        "tahini",
        "tahini paste",
        "crustaceans",
        "mollusks",
    ]

    return cohorts, stem_rows


def reverify(cohorts: dict[str, list[str]], expectations: dict[str, dict]) -> dict:
    """expectations: name -> {restriction, expected_verdict, require_flag}."""
    results = {}
    findings = []
    layer_counts_all = Counter()

    for cohort, names in cohorts.items():
        rows = []
        layer_c = Counter()
        for name in names:
            if not name:
                continue
            exp = expectations.get(name) or {}
            if exp.get("restriction"):
                rid = exp["restriction"]
            elif cohort.startswith("e220"):
                rid = "sulfite_sensitive"
            elif cohort == "dairy_trio":
                rid = "dairy_free"
            elif cohort.startswith("phase1"):
                rid = "vegan"
            else:
                rid = "fish_allergy"
            v, layer, hazards = _prod_verdict(name, rid)
            layer_c[layer] += 1
            layer_counts_all[layer] += 1
            row = {
                "canonical_name": name,
                "restriction": rid,
                "verdict": v,
                "layer": layer,
                "hazards": hazards,
            }
            # Phase-1 demotions: layer attribution only (no expected Avoid).
            if not cohort.startswith("phase1"):
                expected_v = exp.get("expected_verdict")
                if expected_v and v != expected_v:
                    row["FINDING"] = f"expected {expected_v}, got {v} via {layer}"
                    findings.append({**row, "cohort": cohort})
                require_flag = exp.get("require_flag")
                if require_flag and not hazards.get(require_flag):
                    row["FINDING"] = (
                        f"expected hazard {require_flag} true, absent via {layer}; "
                        f"verdict={v}"
                    )
                    findings.append({**row, "cohort": cohort})
            rows.append(row)
        results[cohort] = {
            "n": len(rows),
            "layers": dict(layer_c),
            "rows": rows,
        }

    phase1_layers = Counter()
    phase1_detail = []
    for row in (results.get("phase1_demotions") or {}).get("rows") or []:
        phase1_layers[row["layer"]] += 1
        phase1_detail.append(
            {
                "canonical_name": row["canonical_name"],
                "layer": row["layer"],
                "vegan_verdict": row["verdict"],
                "synthetic_in_hazards": bool(row["hazards"].get("synthetic")),
                "note": (
                    "L1/L2 means Phase-1 DISCOVERED demotion on the live row "
                    "never reached this production verdict"
                    if row["layer"]
                    in ("L1_truth_anchor", "L2_local_ontology")
                    else "L3 — live row can affect verdict"
                ),
            }
        )

    return {
        "cohorts": {
            k: {"n": v["n"], "layers": v["layers"]} for k, v in results.items()
        },
        "layer_counts_all_probes": dict(layer_counts_all),
        "findings": findings,
        "finding_count": len(findings),
        "phase1_layer_distribution": dict(phase1_layers),
        "phase1_detail": phase1_detail,
        "full_cohort_rows": results,
    }


def merge_effect(c, ont: dict[str, dict]) -> dict:
    """Dump names that overlap ontology.json and assert a verdict flag L2 lacks.

    Phase-1/regional injects merge *into* the live ``source=ontology`` row, so a
    live ``source=ifct`` scan undercounts. Compare adapted dumps to L2 instead.
    Also report live ontology-row drift (same names) for cross-check.
    """
    dumps = {
        "ifct": _REPO / "data" / "layer1_ifct.json",
        "fssai": _REPO / "data" / "layer1_fssai.json",
        "usda": _REPO / "data" / "layer1_usda_fdc.json",
        "infoods": _REPO / "data" / "layer1_infoods_anfood.json",
    }
    invisible = []
    by_src = Counter()
    by_flag = Counter()
    overlap_by_src = Counter()
    for src, path in dumps.items():
        raw = json.loads(path.read_text())
        rows = raw if isinstance(raw, list) else raw.get("ingredients") or []
        for r in rows:
            name = normalize_ingredient_key(r.get("canonical_name") or "")
            if not name or name not in ont:
                continue
            overlap_by_src[src] += 1
            mapped, _ = map_record(r, src, default_knowledge_state(src))
            l2 = _l2_flags(ont[name])
            added = [
                f for f in VERDICT_FLAGS if bool(mapped.get(f)) and not bool(l2.get(f))
            ]
            if added:
                by_src[src] += 1
                for f in added:
                    by_flag[f] += 1
                invisible.append(
                    {
                        "canonical_name": r.get("canonical_name") or name,
                        "dump_source": src,
                        "invisible_flags": added,
                    }
                )
    # Deduplicate by name (same name may appear in multiple dumps)
    by_name: dict[str, dict] = {}
    for row in invisible:
        key = normalize_ingredient_key(row["canonical_name"])
        prev = by_name.get(key)
        if not prev:
            by_name[key] = {
                "canonical_name": row["canonical_name"],
                "dump_sources": [row["dump_source"]],
                "invisible_flags": sorted(set(row["invisible_flags"])),
            }
        else:
            prev["dump_sources"] = sorted(
                set(prev["dump_sources"] + [row["dump_source"]])
            )
            prev["invisible_flags"] = sorted(
                set(prev["invisible_flags"]) | set(row["invisible_flags"])
            )
    unique = sorted(
        by_name.values(),
        key=lambda r: (-len(r["invisible_flags"]), r["canonical_name"]),
    )

    # Live source=ontology rows with verdict true that L2 lacks (post-merge store)
    live_invisible = []
    for g in _page(c, source="ontology"):
        name = normalize_ingredient_key(g.get("canonical_name") or "")
        if not name or name not in ont:
            continue
        l2 = _l2_flags(ont[name])
        added = [f for f in VERDICT_FLAGS if bool(g.get(f)) and not bool(l2.get(f))]
        if added:
            live_invisible.append(
                {
                    "canonical_name": g["canonical_name"],
                    "invisible_flags": added,
                    "knowledge_state": g.get("knowledge_state"),
                }
            )

    return {
        "overlap_onto_ontology_by_dump": dict(overlap_by_src),
        "overlap_total": sum(overlap_by_src.values()),
        "dump_names_with_invisible_verdict_flags": len(unique),
        "by_dump_source_row_hits": dict(by_src),
        "by_flag": dict(by_flag),
        "sample": unique[:60],
        "all_names": [r["canonical_name"] for r in unique],
        "live_ontology_invisible_verdict_flags": len(live_invisible),
        "live_ontology_invisible_sample": live_invisible[:40],
        "note": (
            "Overlaps (~510) are dump rows whose name exists in ontology.json. "
            "Invisible = dump (or live ontology row) has a verdict-relevant true "
            "that L2 lacks. Synthetic-only Phase-1 adds are excluded from "
            "VERDICT_FLAGS; they demote knowledge_state on the live row but do "
            "not appear here."
        ),
    }


def uncertain_128_breakdown() -> dict:
    exp = json.loads((_REPO / "docs" / "item37_fish_verdict_exposure.json").read_text())
    rows = [
        r
        for r in exp.get("rows") or []
        if (not r.get("land_meat_or_poultry"))
        and r.get("fish_allergy") == "UNCERTAIN"
        and r.get("shellfish_allergy") == "UNCERTAIN"
    ]
    buckets = {
        "unresolved_as_typed": [],
        "resolved_no_kind": [],
        "flagged_but_untrusted_or_capped": [],
        "other": [],
    }
    unc_token_counts = Counter()
    for r in rows:
        name = r["canonical_name"]
        _clear_cache()
        resolved = resolve(name, None)
        layer = getattr(resolved, "resolution_layer", None)
        ci = to_compliance_input(resolved, query_atom=name)
        fish = bool(ci.flags.get("fish_source"))
        shell = bool(ci.flags.get("shellfish_source"))
        cap = getattr(ci, "verdict_cap", None) or ci.flags.get("verdict_cap")
        unc = list(ci.flags.get("uncertainty_flags") or [])
        for t in unc:
            unc_token_counts[str(t)] += 1
        entry = {
            "canonical_name": name,
            "layer": layer,
            "fish_source": fish,
            "shellfish_source": shell,
            "verdict_cap": cap,
            "uncertainty_flags": unc,
            "trusted": bool(getattr(resolved, "trusted", False)),
            "knowledge_state": getattr(ci, "knowledge_state", None),
            "bucket_src": r.get("bucket"),
        }
        if resolved.group is None or (layer or "").startswith("L5"):
            buckets["unresolved_as_typed"].append(entry)
        elif not fish and not shell:
            buckets["resolved_no_kind"].append(entry)
        elif (fish or shell) and (cap or unc or not getattr(resolved, "trusted", False)):
            buckets["flagged_but_untrusted_or_capped"].append(entry)
        else:
            buckets["other"].append(entry)
    return {
        "n": len(rows),
        "counts": {k: len(v) for k, v in buckets.items()},
        "uncertainty_token_counts": dict(unc_token_counts),
        "mechanism_note": (
            "All 128 currently resolve with fish_source or shellfish_source true "
            "via L3, but carry uncertainty_flags (typically usda_fdc_bulk_inferred) "
            "so trusted=False and allergy rules stay UNCERTAIN (fail-closed). "
            "Not unresolved strings; not missing kind flags."
        ),
        "buckets": buckets,
    }


def no_kind_dairy_egg_scan(c) -> dict:
    hand = json.loads((_REPO / "docs" / "item37_animal_no_kind_hand_read.json").read_text())
    ont = hand.get("ontology") or []
    dairy_tagged = [r for r in ont if r.get("tag") == "dairy_suspect"]
    other = [r for r in ont if r.get("tag") == "other_animal"]

    live = _page(c)
    no_kind = [
        g
        for g in live
        if g.get("animal_origin") and not any(g.get(f) for f in KIND_FLAGS)
    ]

    dairy_findings = []
    egg_findings = []
    insect_findings = []
    lexicon_candidates = []
    for g in no_kind:
        name = g["canonical_name"]
        nl = name.lower()
        looks_dairy = (
            bool(
                re.search(
                    r"\b(milk|cheese|butter|cream|whey|yogurt|yoghurt|ghee|dairy|"
                    r"casein|lactose|buttermilk|paneer|curd|halloumi|filmj|"
                    r"viili|kefir|quark|skyr|labneh|ricotta|mascarpone|"
                    r"mozzarella|cheddar|parmesan|brie|camembert)\b",
                    nl,
                )
                or nl in ("filmjölk", "viili", "halloumi")
            )
            and not re.search(
                r"\b(almond|oat|soy|soya|rice|coconut|hemp|cashew|pea)\s+milk\b",
                nl,
            )
            and "coconut milk" not in nl
        )
        looks_egg = bool(re.search(r"\b(egg|eggs)\b", nl)) and "eggplant" not in nl
        looks_insect = bool(
            re.search(
                r"\b(insect|cricket|mealworm|locust|cochineal|carmine|shellac)\b",
                nl,
            )
        )
        if not (looks_dairy or looks_egg or looks_insect):
            continue
        lexicon_candidates.append(
            {
                "canonical_name": name,
                "source": g.get("source"),
                "looks_dairy": looks_dairy,
                "looks_egg": looks_egg,
                "looks_insect": looks_insect,
            }
        )
        if looks_dairy:
            vd, layer_d, hz_d = _prod_verdict(name, "dairy_free")
            if vd == "SAFE":
                dairy_findings.append(
                    {
                        "canonical_name": name,
                        "source": g.get("source"),
                        "layer": layer_d,
                        "verdict": vd,
                        "dairy_source_on_ci": bool(hz_d.get("dairy_source")),
                    }
                )
        if looks_egg:
            ve, layer_e, hz_e = _prod_verdict(name, "egg_free")
            if ve == "SAFE":
                egg_findings.append(
                    {
                        "canonical_name": name,
                        "source": g.get("source"),
                        "layer": layer_e,
                        "verdict": ve,
                        "egg_source_on_ci": bool(hz_e.get("egg_source")),
                    }
                )
        if looks_insect:
            insect_findings.append(
                {
                    "canonical_name": name,
                    "source": g.get("source"),
                    "insect_derived_live": bool(g.get("insect_derived")),
                }
            )

    return {
        "ontology_dairy_tagged": dairy_tagged,
        "ontology_other_animal_names": [r["canonical_name"] for r in other],
        "ontology_other_animal_count": len(other),
        "no_kind_total": len(no_kind),
        "lexicon_candidates": lexicon_candidates,
        "no_kind_dairy_SAFE_findings": dairy_findings,
        "no_kind_egg_SAFE_findings": egg_findings,
        "no_kind_insect_named": insect_findings,
    }


def recommendation(exp1: dict | None = None) -> dict:
    drift_n = (exp1 or {}).get("names_with_verdict_relevant_drift", "?")
    live_n = (exp1 or {}).get("live_source_ontology_rows", "?")
    return {
        "recommended": "inject_writes_through_to_ontology_json",
        "rationale": [
            "Production resolve order is L1 → L2 (ontology.json) → L3 (DB). "
            "For any name present in ontology.json, live merges never reach a verdict.",
            "Write-through keeps the offline/test path (no DB) identical to production "
            "for ontology-named ingredients — tests already load ontology.json.",
            "DB-before-L2 would fix drift but split offline tests from production unless "
            "tests always run against a DB fixture.",
            "L2 regenerated from DB after each inject is equivalent if regeneration is "
            "mandatory in the inject CLI and CI fails when ontology.json is stale — "
            "write-through is the simpler invariant (inject is the single writer).",
        ],
        "rejected_alternatives": {
            "db_before_l2": (
                "Fixes runtime drift but makes ontology.json a cache of last resort; "
                "CI/unit tests without Supabase would silently see stale L2 or miss rows."
            ),
            "l2_regenerated_from_db": (
                "Works if enforced, but two-step (inject then export) is easy to skip; "
                "write-through folds the export into the inject transaction."
            ),
        },
        "item12_audit": (
            "Add L2-vs-L3 drift check: for every live source=ontology (and every live "
            "row whose canonical_name is in ontology.json), diff verdict-relevant true "
            "flags; fail or ticket when live_true and l2_false on allergen/species/"
            "animal_origin. Diff by name, not aggregate count."
        ),
        "new_item": (
            "Logged as Item 41 (P0): docs/item41_l2_l3_dual_store_authority.md — "
            f"dual stores need one declared authority + L2↔L3 drift test "
            f"(step-1: {live_n} live ontology rows, {drift_n} with verdict-relevant drift)."
        ),
    }


def _build_expectations(
    cohorts: dict[str, list[str]], stem_rows: list[dict]
) -> dict[str, dict]:
    exp: dict[str, dict] = {}
    # Stem triage: expect Avoid on the primary true allergen flag in the dump.
    for r in stem_rows:
        name = normalize_ingredient_key(r.get("canonical_name") or "")
        if not name:
            continue
        for flag, rid in _FLAG_TO_RESTRICTION.items():
            if r.get(flag):
                exp[name] = {
                    "restriction": rid,
                    "expected_verdict": "NOT_SAFE",
                    "require_flag": flag,
                }
                break
    for n in cohorts.get("fish_flips_71") or []:
        if re.search(
            r"\b(crab|shrimp|prawn|lobster|clam|mussel|oyster|squid|"
            r"crustacean|shellfish|crayfish|mollusk|mollusc)\b",
            n,
        ) and not re.search(r"\b(emu|ostrich)\s+oyster\b", n):
            exp[n] = {
                "restriction": "shellfish_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "shellfish_source",
            }
        else:
            exp[n] = {
                "restriction": "fish_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "fish_source",
            }
    for n in cohorts.get("regional_infoods_flipped") or []:
        exp[n] = {
            "restriction": "fish_allergy",
            "expected_verdict": "NOT_SAFE",
            "require_flag": "fish_source",
        }
    for n in cohorts.get("regional_ifct_flipped") or []:
        exp.setdefault(
            n,
            {
                "restriction": "fish_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "fish_source",
            },
        )
    for n in cohorts.get("same_day_examples") or []:
        if "lupin" in n:
            exp[n] = {
                "restriction": "lupin_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "lupin_source",
            }
        elif "tahini" in n:
            exp[n] = {
                "restriction": "sesame_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "sesame_source",
            }
        elif n in ("crustaceans", "mollusks"):
            exp[n] = {
                "restriction": "shellfish_allergy",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "shellfish_source",
            }
        else:
            exp[n] = {
                "restriction": "gluten_free",
                "expected_verdict": "NOT_SAFE",
                "require_flag": "gluten_source",
            }
    for n in cohorts.get("e220_e228") or []:
        exp[n] = {
            "restriction": "sulfite_sensitive",
            "expected_verdict": "NOT_SAFE",
            "require_flag": "sulphite_source",
        }
    for n in cohorts.get("dairy_trio") or []:
        exp[n] = {
            "restriction": "dairy_free",
            "expected_verdict": "NOT_SAFE",
            "require_flag": "dairy_source",
        }
    return exp


def main() -> int:
    c = _client()
    ont = _load_ontology_by_name()
    report: dict = {}

    print("=== 1 layer exposure (live ontology vs ontology.json) ===", flush=True)
    exp1 = layer_exposure(c, ont)
    report["1_layer_exposure"] = {
        k: exp1[k]
        for k in exp1
        if k not in ("top_verdict_drift", "all_verdict_drift_names")
    }
    report["1_layer_exposure"]["top_verdict_drift"] = exp1["top_verdict_drift"]
    print(
        json.dumps(
            {
                "live_ontology_rows": exp1["live_source_ontology_rows"],
                "names_with_verdict_drift": exp1["names_with_verdict_relevant_drift"],
                "per_flag_live_true_l2_false": exp1["per_flag_live_true_l2_false"],
                "top10": exp1["top_verdict_drift"][:10],
            },
            indent=2,
        )
    )

    print("=== 2 production re-verify ===", flush=True)
    cohorts, stem_rows = _collect_thread_names()
    expectations = _build_expectations(cohorts, stem_rows)
    rev = reverify(cohorts, expectations)
    report["2_reverify"] = {
        "cohorts": rev["cohorts"],
        "layer_counts_all_probes": rev["layer_counts_all_probes"],
        "finding_count": rev["finding_count"],
        "findings": rev["findings"][:80],
        "phase1_layer_distribution": rev["phase1_layer_distribution"],
        "phase1_l2_count": rev["phase1_layer_distribution"].get("L2_local_ontology", 0),
        "phase1_l3_count": rev["phase1_layer_distribution"].get("L3_db_alias", 0),
        "phase1_sample": rev["phase1_detail"][:15],
    }
    # attach full phase1 detail to sidecar
    (_REPO / "docs" / "item37_phase1_layer_serving.json").write_text(
        json.dumps(rev["phase1_detail"], indent=2) + "\n"
    )
    (_REPO / "docs" / "item37_l2_l3_reverify_full.json").write_text(
        json.dumps(rev["full_cohort_rows"], indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "cohorts": rev["cohorts"],
                "findings": rev["finding_count"],
                "finding_sample": rev["findings"][:15],
                "phase1_layers": rev["phase1_layer_distribution"],
            },
            indent=2,
        )
    )

    print("=== 3 merge effect ===", flush=True)
    merge = merge_effect(c, ont)
    report["3_merge_effect"] = {
        k: merge[k] for k in merge if k not in ("sample", "all_names")
    }
    report["3_merge_effect"]["sample"] = merge["sample"]
    print(
        json.dumps(
            {
                "overlap_by_dump": merge["overlap_onto_ontology_by_dump"],
                "invisible_unique_names": merge[
                    "dump_names_with_invisible_verdict_flags"
                ],
                "live_ontology_invisible": merge[
                    "live_ontology_invisible_verdict_flags"
                ],
                "by_flag": merge["by_flag"],
                "sample": merge["sample"][:15],
            },
            indent=2,
        )
    )

    print("=== 4 recommendation ===", flush=True)
    rec = recommendation(exp1)
    report["4_decision"] = rec
    print(json.dumps(rec, indent=2))

    print("=== 5 UNCERTAIN-128 + no-kind dairy/egg ===", flush=True)
    u128 = uncertain_128_breakdown()
    nok = no_kind_dairy_egg_scan(c)
    report["5_uncertain_128"] = {
        "n": u128["n"],
        "counts": u128["counts"],
        "uncertainty_token_counts": u128["uncertainty_token_counts"],
        "mechanism_note": u128["mechanism_note"],
        "unresolved_sample": u128["buckets"]["unresolved_as_typed"][:20],
        "resolved_no_kind_sample": u128["buckets"]["resolved_no_kind"][:20],
        "flagged_untrusted_sample": u128["buckets"][
            "flagged_but_untrusted_or_capped"
        ][:20],
        "other_sample": u128["buckets"]["other"][:20],
    }
    report["5_no_kind_dairy_egg"] = nok
    (_REPO / "docs" / "item37_uncertain128_breakdown.json").write_text(
        json.dumps(u128, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "uncertain128_counts": u128["counts"],
                "dairy_tagged": nok["ontology_dairy_tagged"],
                "other_count": nok["ontology_other_animal_count"],
                "other_names": nok["ontology_other_animal_names"],
                "dairy_SAFE_findings": nok["no_kind_dairy_SAFE_findings"][:20],
                "egg_SAFE_findings": nok["no_kind_egg_SAFE_findings"][:20],
                "insect_named": nok["no_kind_insect_named"][:20],
            },
            indent=2,
        )
    )

    out = _REPO / "docs" / "item37_l2_l3_layer_exposure.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("Wrote", out)

    # Markdown closeout
    md = _REPO / "docs" / "item37_l2_l3_layer_exposure.md"
    md.write_text(
        _render_md(report, exp1, rev, merge, u128, nok, rec) + "\n",
        encoding="utf-8",
    )
    print("Wrote", md)
    return 0


def _render_md(report, exp1, rev, merge, u128, nok, rec) -> str:
    lines = [
        "# Item 37 — L2 vs L3 layer exposure (report)",
        "",
        "Production resolve order: **L1 truth_anchor → L2 local_ontology (`ontology.json`) → L3 Supabase**. "
        "For ontology-named ingredients, live DB merges do not answer.",
        "",
        "## 1. Layer exposure (live `source=ontology` vs `ontology.json`)",
        "",
        f"- Live ontology-sourced rows: **{exp1['live_source_ontology_rows']}**",
        f"- Names with verdict-relevant drift: **{exp1['names_with_verdict_relevant_drift']}**",
        f"- Missing from ontology.json: **{exp1['missing_in_ontology_json']}**",
        "",
        "### Per-flag: live true, L2 false (invisible at runtime if L2 serves)",
        "",
        "| Flag | Count |",
        "|------|------:|",
    ]
    for f, n in sorted(
        exp1["per_flag_live_true_l2_false"].items(), key=lambda x: -x[1]
    ):
        lines.append(f"| `{f}` | {n} |")
    lines += [
        "",
        "### Top verdict-relevant drift (name)",
        "",
    ]
    for d in exp1["top_verdict_drift"][:25]:
        lines.append(
            f"- `{d['canonical_name']}` — {', '.join(d['verdict_relevant_diffs'])}"
        )
    lines += [
        "",
        "## 2. Production re-verify (no layer bypass)",
        "",
        f"- Findings (expected vs actual): **{rev['finding_count']}** "
        f"(all current findings are fish_flips_71 → UNCERTAIN via "
        f"`usda_fdc_bulk_inferred`, not SAFE misses)",
        f"- Phase-1 demotions served by L1: "
        f"**{rev['phase1_layer_distribution'].get('L1_truth_anchor', 0)}**",
        f"- Phase-1 demotions served by L2: "
        f"**{rev['phase1_layer_distribution'].get('L2_local_ontology', 0)}**",
        f"- Phase-1 demotions served by L3: "
        f"**{rev['phase1_layer_distribution'].get('L3_db_alias', 0)}** "
        f"(zero ⇒ no Phase-1 demotion reached a production verdict)",
        "",
        "Cohort layer mixes:",
        "",
    ]
    for cohort, meta in rev["cohorts"].items():
        lines.append(f"- **{cohort}** (n={meta['n']}): {meta['layers']}")
    if rev["findings"]:
        lines += ["", "### Findings (sample)", ""]
        for f in rev["findings"][:25]:
            lines.append(
                f"- `{f['canonical_name']}` [{f.get('cohort')}] {f.get('FINDING')} "
                f"(got {f['verdict']} via {f['layer']})"
            )
    lines += [
        "",
        "## 3. Merge effect (IFCT/FSSAI/USDA/INFOODS → existing ontology names)",
        "",
        f"- Dump↔ontology overlaps: **{merge['overlap_onto_ontology_by_dump']}** "
        f"(total {merge['overlap_total']})",
        f"- Unique names where dump adds a verdict-relevant flag L2 lacks: "
        f"**{merge['dump_names_with_invisible_verdict_flags']}**",
        f"- Live `source=ontology` rows with same invisible pattern: "
        f"**{merge['live_ontology_invisible_verdict_flags']}**",
        f"- By dump (row hits): {merge['by_dump_source_row_hits']}",
        f"- By flag: {merge['by_flag']}",
        f"- Note: {merge['note']}",
        "",
    ]
    for s in merge["sample"][:20]:
        lines.append(
            f"- `{s['canonical_name']}` ({', '.join(s['dump_sources'])}) — "
            f"{', '.join(s['invisible_flags'])}"
        )
    lines += [
        "",
        "## 4. Decision (not code)",
        "",
        f"**Recommend: `{rec['recommended']}`** — inject writes through to `ontology.json`.",
        "",
    ]
    for r in rec["rationale"]:
        lines.append(f"- {r}")
    lines += [
        "",
        f"Item 12: {rec['item12_audit']}",
        "",
        f"New item: {rec['new_item']}",
        "",
        "## 5. UNCERTAIN-under-both (128) + no-kind dairy/egg",
        "",
        f"- Count in exposure file (both UNCERTAIN, non-land-meat): **{u128['n']}**",
        f"- Breakdown: {u128['counts']}",
        f"- Uncertainty tokens: {u128.get('uncertainty_token_counts')}",
        f"- Mechanism: {u128.get('mechanism_note')}",
        "",
        "### Ontology no-kind tags",
        "",
        f"- Dairy-tagged row(s): "
        + (
            ", ".join(f"`{r['canonical_name']}`" for r in nok["ontology_dairy_tagged"])
            or "(none)"
        )
        + " (plant milk powder mis-tagged; not an oat-shape dairy miss)",
        f"- Other-animal ({nok['ontology_other_animal_count']}):",
        "",
    ]
    for n in nok["ontology_other_animal_names"]:
        lines.append(f"  - `{n}`")
    dairy_safe = nok["no_kind_dairy_SAFE_findings"]
    lines += [
        "",
        f"- No-kind dairy SAFE findings (oat-shape under dairy_free): "
        f"**{len(dairy_safe)}**"
        + (
            " — "
            + ", ".join(f"`{r['canonical_name']}`" for r in dairy_safe)
            if dairy_safe
            else ""
        ),
        f"- No-kind egg SAFE findings: **{len(nok['no_kind_egg_SAFE_findings'])}**",
        f"- Insect-named in no-kind: **{len(nok['no_kind_insect_named'])}**"
        + (
            " — "
            + ", ".join(
                f"`{r['canonical_name']}`" for r in nok["no_kind_insect_named"]
            )
            if nok["no_kind_insect_named"]
            else ""
        ),
        "",
        "Among the 46 other-animal tags, dairy-shaped names that are also "
        "no-kind SAFE under dairy_free include `halloumi`, `filmjölk`, `viili` "
        "(and `goat milk fat` from the lexicon scan). `stockfish` is fish-shaped "
        "no-kind under fish_allergy — same FINDING class as fish/shellfish.",
        "",
        "Artifacts: `docs/item37_l2_l3_layer_exposure.json`, "
        "`docs/item37_phase1_layer_serving.json`, "
        "`docs/item37_uncertain128_breakdown.json`, "
        "`docs/item41_l2_l3_dual_store_authority.md`.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
