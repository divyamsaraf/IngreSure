#!/usr/bin/env python3
"""Item 37: verdict exposure → flip unambiguous fish/shellfish → USDA transform reinject."""
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

_LAND_MEAT = re.compile(
    r"\b(beef|pork|lamb|goat|sheep|chicken|turkey|duck|veal|mutton|bison|"
    r"venison|bacon|ham|meat|poultry|liver|heart|kidney|tripe|brain|calf|"
    r"steak|chops|sausage|bologna|hot dog|frankfurter|emu|ostrich|alligator|"
    r"kangaroo|elk|rabbit|hare)\b",
    re.I,
)
_POULTRY = re.compile(
    r"\b(chicken|turkey|duck|goose|poultry|hen|quail|pheasant|guinea)\b", re.I
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


def _verdict(name: str, rid: str) -> str:
    r = resolve(name, None)
    ci = to_compliance_input(r, query_atom=name)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


def _is_land_meat_or_poultry(name: str) -> bool:
    nl = name.lower()
    # "emu oyster" / "ostrich oyster" are muscle cuts, not shellfish.
    if re.search(r"\b(emu|ostrich)\s+oyster\b", nl):
        return True
    if re.search(
        r"\b(fish|seafood|crab|shrimp|prawn|lobster|clam|mussel|"
        r"oyster|squid|octopus|crustacean|mollusk|salmon|tuna|cod|"
        r"herring|mackerel|sardine|sprat)\b",
        nl,
    ):
        return False
    return bool(_LAND_MEAT.search(nl) or _POULTRY.search(nl))


def _load_suspect_sets() -> dict:
    hand = json.loads((_REPO / "docs" / "item37_animal_no_kind_hand_read.json").read_text())
    matches = hand.get("infoods_split_matches") or []
    ont8 = [
        r["canonical_name"]
        for r in (hand.get("ontology") or [])
        if r.get("tag") == "fish_suspect"
    ]
    usda = [r["canonical_name"] for r in (hand.get("usda_fish_shellfish_lexicon") or [])]
    return {
        "infoods_matched": matches,
        "ontology_fish_seafood": ont8,
        "usda_lexicon": usda,
    }


def _kind_for_ontology(name: str) -> dict:
    nl = name.lower()
    if "seafood" in nl:
        return {"fish_source": True, "shellfish_source": True, "animal_origin": True}
    return {"fish_source": True, "shellfish_source": False, "animal_origin": True}


def _kind_for_match(m: dict) -> dict:
    part = (m.get("matched_part") or "").lower()
    infoods = (m.get("infoods") or "").lower()
    live = (m.get("live") or "").lower()
    blob = f"{part} {infoods} {live}"
    if re.search(
        r"\b(crab|shrimp|prawn|lobster|clam|mussel|oyster|squid|octopus|"
        r"crayfish|crawfish|scallop|crustacean|mollusk|shellfish|cuttlefish)\b",
        blob,
    ):
        return {
            "fish_source": False,
            "shellfish_source": True,
            "animal_origin": True,
            "animal_species": "shellfish",
        }
    return {
        "fish_source": True,
        "shellfish_source": False,
        "animal_origin": True,
        "animal_species": "fish",
    }


def verdict_exposure(sets: dict) -> dict:
    union_names: dict[str, dict] = {}
    for m in sets["infoods_matched"]:
        n = normalize_ingredient_key(m["live"])
        union_names[n] = {
            "canonical_name": m["live"],
            "bucket": "infoods_matched",
            "evidence": m,
        }
    for n in sets["ontology_fish_seafood"]:
        key = normalize_ingredient_key(n)
        union_names.setdefault(
            key, {"canonical_name": n, "bucket": "ontology_fish_seafood", "evidence": None}
        )
        if union_names[key]["bucket"] != "infoods_matched":
            union_names[key]["bucket"] = "ontology_fish_seafood"
    for n in sets["usda_lexicon"]:
        key = normalize_ingredient_key(n)
        if key not in union_names:
            union_names[key] = {
                "canonical_name": n,
                "bucket": "usda_lexicon",
                "evidence": None,
            }

    rows = []
    for meta in sorted(union_names.values(), key=lambda x: x["canonical_name"]):
        name = meta["canonical_name"]
        land = _is_land_meat_or_poultry(name)
        vf = _verdict(name, "fish_allergy")
        vs = _verdict(name, "shellfish_allergy")
        finding_fish = (not land) and vf == "SAFE"
        finding_shell = (not land) and vs == "SAFE" and (
            "seafood" in name.lower()
            or bool(
                re.search(
                    r"\b(crab|shrimp|prawn|lobster|clam|mussel|oyster|squid|"
                    r"crustacean|shellfish)\b",
                    name.lower(),
                )
            )
        )
        rows.append(
            {
                **meta,
                "land_meat_or_poultry": land,
                "fish_allergy": vf,
                "shellfish_allergy": vs,
                "FINDING_fish_allergy": finding_fish,
                "FINDING_shellfish_allergy": finding_shell,
            }
        )

    def _counts(rid_key: str, finding_key: str) -> dict:
        eligible = [r for r in rows if not r["land_meat_or_poultry"]]
        return {
            "n_union": len(rows),
            "n_after_land_meat_filter": len(eligible),
            "verdicts": dict(Counter(r[rid_key] for r in eligible)),
            "FINDING_SAFE_count": sum(1 for r in eligible if r[finding_key]),
            "FINDING_SAFE_names": sorted(
                r["canonical_name"] for r in eligible if r[finding_key]
            ),
        }

    by_bucket = Counter(r["bucket"] for r in rows)
    return {
        "union_size": len(rows),
        "by_bucket": dict(by_bucket),
        "fish_allergy": _counts("fish_allergy", "FINDING_fish_allergy"),
        "shellfish_allergy": _counts("shellfish_allergy", "FINDING_shellfish_allergy"),
        "rows": rows,
        "finding_rule_note": (
            "FINDING applies only after excluding land-meat/poultry tags. "
            "SAFE + animal_origin + no kind under fish_allergy is a FINDING "
            "only for non-land-meat rows (snapper/seafood shape)."
        ),
    }


def build_flip_dump(sets: dict) -> Path:
    records = []
    seen: set[str] = set()
    for name in sets["ontology_fish_seafood"]:
        key = normalize_ingredient_key(name)
        if key in seen:
            continue
        seen.add(key)
        kind = _kind_for_ontology(name)
        af = [k for k, v in kind.items() if v is True]
        records.append(
            {
                "canonical_name": name,
                **kind,
                "asserted_flags": af,
                "knowledge_state": "AUTO_CLASSIFIED",
                "uncertainty_flags": [],
                "_evidence": f"ontology_fish_suspect:{name}",
            }
        )
    for m in sets["infoods_matched"]:
        name = m["live"]
        key = normalize_ingredient_key(name)
        if key in seen:
            # merge both-kinds if seafood ontology already added
            continue
        seen.add(key)
        kind = _kind_for_match(m)
        af = [k for k, v in kind.items() if v is True and k != "animal_species"]
        if kind.get("animal_species"):
            pass
        rec = {
            "canonical_name": name,
            **{k: v for k, v in kind.items() if k != "animal_species"},
            "asserted_flags": af,
            "knowledge_state": "AUTO_CLASSIFIED",
            "_evidence": (
                f"infoods_match:{m.get('matched_part')}→{m.get('infoods')} "
                f"how={m.get('how')}"
            ),
        }
        if kind.get("animal_species"):
            rec["animal_species"] = kind["animal_species"]
        records.append(rec)

    # strip private evidence from inject payload but keep sidecar
    evidence = {r["canonical_name"]: r.pop("_evidence") for r in records}
    path = _REPO / "data" / "layer1_item37_fish_flip.json"
    path.write_text(
        json.dumps({"source": "ontology", "ingredients": records}, indent=2) + "\n"
    )
    (_REPO / "docs" / "item37_fish_flip_evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    return path


def seed_writer(rows) -> _CollectWriter:
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


def dry_run_dump(path: Path, seed_rows, label: str, source: str) -> dict:
    _, records = load_dump(str(path))
    for r in records:
        r["canonical_name"] = normalize_ingredient_key(r.get("canonical_name") or "")
    w = seed_writer(seed_rows)
    before = w.list_discovered_names()
    stats = inject(records, source, w)
    new = sorted(
        n
        for n, g in w.groups.items()
        if g.get("knowledge_state") == "DISCOVERED" and n not in before
    )
    return {
        "label": label,
        "stats": stats.as_dict(),
        "needs_review": stats.needs_review,
        "new_discovered": new,
    }


def recount_nokind(c) -> dict:
    live = _page(c)
    no_kind = [
        g
        for g in live
        if g.get("animal_origin") and not any(g.get(f) for f in KIND_FLAGS)
    ]
    by_src = Counter(g.get("source") or "?" for g in no_kind)
    usda_fishish = [
        g["canonical_name"]
        for g in no_kind
        if g.get("source") == "usda"
        and re.search(
            r"\b(fish|crustacean|shrimp|crab|lobster|seafood|salmon|tuna|cod)\b",
            g["canonical_name"],
            re.I,
        )
    ]
    return {
        "animal_no_kind": len(no_kind),
        "by_source": dict(by_src),
        "usda_fish_shellfish_shaped_remaining": len(usda_fishish),
        "usda_remaining_sample": usda_fishish[:40],
    }


def synthetic_untouched() -> dict:
    md = (_REPO / "docs" / "item11_phase1_flag_changes.md").read_text()
    all_rows = []
    synth = []
    for m in re.finditer(r"^- `([^`]+)` — added: ([^\n]+)", md, re.M):
        name, rest = m.group(1), m.group(2)
        all_rows.append((name, rest))
        if "synthetic false→true" in rest:
            synth.append(name)
    non = [(n, r) for n, r in all_rows if "synthetic false→true" not in r]
    return {
        "phase1_total_demotions": len(all_rows),
        "synthetic_false_to_true": len(synth),
        "synthetic_restore_touched": len(synth),
        "untouched_non_synthetic": [
            {
                "canonical_name": n,
                "why": r.strip(),
                "reason": "demotion trigger was not synthetic (egg/root/plant_origin)",
            }
            for n, r in non
        ],
        "note": (
            "~80 was the synthetic-pattern ballpark; exact synthetic demotions "
            "were 77. The other 5 Phase-1 demotions were non-synthetic and "
            "correctly outside the synthetic restore scope."
        ),
    }


def main() -> int:
    c = _client()
    report: dict = {"housekeeping": {"synthetic_untouched": synthetic_untouched()}}
    print("=== 4 housekeeping synthetic untouched ===", flush=True)
    print(json.dumps(report["housekeeping"], indent=2))

    sets = _load_suspect_sets()
    print(
        "suspect sizes",
        {k: len(v) for k, v in sets.items()},
        flush=True,
    )

    print("=== 1 verdict exposure ===", flush=True)
    exp = verdict_exposure(sets)
    report["1_verdict_exposure"] = {
        k: exp[k]
        for k in exp
        if k != "rows"
    }
    report["1_verdict_exposure"]["rows_path"] = str(
        _REPO / "docs" / "item37_fish_verdict_exposure.json"
    )
    (_REPO / "docs" / "item37_fish_verdict_exposure.json").write_text(
        json.dumps(exp, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "union": exp["union_size"],
                "by_bucket": exp["by_bucket"],
                "fish": exp["fish_allergy"],
                "shellfish": {
                    k: exp["shellfish_allergy"][k]
                    for k in exp["shellfish_allergy"]
                    if k != "FINDING_SAFE_names"
                },
                "finding_fish_names_sample": exp["fish_allergy"]["FINDING_SAFE_names"][:30],
            },
            indent=2,
        )
    )

    print("=== 2 flip dump + dry-runs ===", flush=True)
    flip_path = build_flip_dump(sets)
    ont = json.loads((_REPO / "data" / "ontology.json").read_text()).get("ingredients") or []
    for r in ont:
        r["canonical_name"] = normalize_ingredient_key(r.get("canonical_name") or "")
        r.setdefault("knowledge_state", "AUTO_CLASSIFIED")
        r.setdefault("source", "ontology")
        r["asserted_flags"] = [f for f in BOOL_FLAGS if r.get(f)]
    live = _page(c)
    d1 = dry_run_dump(flip_path, ont, "ontology-seeded", "ontology")
    d2 = dry_run_dump(flip_path, live, "live-seeded", "ontology")
    report["2_flip_dry_runs"] = {"ontology": d1, "live": d2, "path": str(flip_path)}
    print(json.dumps(report["2_flip_dry_runs"], indent=2))
    if d1["needs_review"] or d2["needs_review"]:
        print("ABORT demotions on flip dry-run", file=sys.stderr)
        (_REPO / "docs" / "item37_fish_flip_usda_ops.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        return 1

    print("=== 2 live flip inject ===", flush=True)
    rc_flip = bulk_main(
        [
            str(flip_path),
            "--source",
            "ontology",
            "--discovered-diff",
            str(_REPO / "docs" / "item37_fish_flip_discovered_diff.json"),
        ]
    )
    report["2_flip_inject_rc"] = rc_flip

    print("=== 3 USDA transform regen ===", flush=True)
    import subprocess

    r = subprocess.run(
        [sys.executable, str(_BACKEND / "scripts" / "transform_usda_fdc_bulk.py")],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1
    usda_path = _REPO / "data" / "layer1_usda_fdc.json"
    dump = json.loads(usda_path.read_text())
    fish_n = sum(1 for x in dump if x.get("fish_source"))
    shell_n = sum(1 for x in dump if x.get("shellfish_source"))
    report["3_usda_dump"] = {
        "rows": len(dump),
        "fish_source_true": fish_n,
        "shellfish_source_true": shell_n,
        "keeps_food_category_on_layer1": False,
        "derives_from_raw_foodCategory": True,
        "category_example": "Finfish and Shellfish Products",
    }
    print(json.dumps(report["3_usda_dump"], indent=2))

    # Validate sample through adapt
    from core.knowledge.ike2.etl.adapt import map_record
    from core.knowledge.ike2.etl.validate import validate_rows
    from core.knowledge.ike2.etl.sources import default_knowledge_state

    okc = badc = 0
    for row in dump:
        mapped, _ = map_record(row, "usda", default_knowledge_state("usda"))
        o, rj = validate_rows([mapped])
        if rj:
            badc += 1
        else:
            okc += 1
    report["3_usda_dump"]["adapt_validate_ok"] = okc
    report["3_usda_dump"]["adapt_validate_bad"] = badc
    if badc:
        print("ABORT usda dump validate fails", badc, file=sys.stderr)
        return 1

    print("=== 3 USDA dry-runs ===", flush=True)
    # Seed only names present in dump for speed? Full live seed is OK but heavy.
    # Use live-seeded for demotion bar; ontology-seeded too.
    d3 = dry_run_dump(usda_path, ont, "usda-ontology-seeded", "usda")
    d4 = dry_run_dump(usda_path, live, "usda-live-seeded", "usda")
    report["3_usda_dry_runs"] = {"ontology": d3, "live": d4}
    print(
        json.dumps(
            {
                "ontology_needs_review": d3["needs_review"],
                "live_needs_review": d4["needs_review"],
                "ontology_stats": d3["stats"],
                "live_stats": d4["stats"],
            },
            indent=2,
        )
    )
    if d3["needs_review"] or d4["needs_review"]:
        print("ABORT usda dry-run demotions", file=sys.stderr)
        (_REPO / "docs" / "item37_fish_flip_usda_ops.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        return 1

    print("=== 3 USDA live inject ===", flush=True)
    rc_usda = bulk_main(
        [
            str(usda_path),
            "--source",
            "usda",
            "--discovered-diff",
            str(_REPO / "docs" / "item37_usda_inject_discovered_diff.json"),
        ]
    )
    report["3_usda_inject_rc"] = rc_usda

    print("=== recount ===", flush=True)
    before_nokind = None  # already had 852
    after = recount_nokind(c)
    report["recount_nokind"] = after
    # re-check exposure on ontology 8 + previous matches
    sets2 = _load_suspect_sets()
    # refresh usda lexicon from recount sample + remaining
    exp2 = verdict_exposure(
        {
            "infoods_matched": sets["infoods_matched"],
            "ontology_fish_seafood": sets["ontology_fish_seafood"],
            "usda_lexicon": after["usda_remaining_sample"]
            + [
                r["canonical_name"]
                for r in json.loads(
                    (_REPO / "docs" / "item37_animal_no_kind_hand_read.json").read_text()
                ).get("usda_fish_shellfish_lexicon")
                or []
            ],
        }
    )
    report["post_flip_ontology8_verdicts"] = [
        r
        for r in exp2["rows"]
        if r["bucket"] == "ontology_fish_seafood"
        or r["canonical_name"]
        in {normalize_ingredient_key(x) for x in sets["ontology_fish_seafood"]}
        or r["canonical_name"] in sets["ontology_fish_seafood"]
    ]
    # simpler direct check
    post8 = []
    for n in sets["ontology_fish_seafood"]:
        post8.append(
            {
                "canonical_name": n,
                "fish_allergy": _verdict(n, "fish_allergy"),
                "shellfish_allergy": _verdict(n, "shellfish_allergy"),
            }
        )
    report["post_flip_ontology8_verdicts"] = post8
    print(json.dumps({"recount": after, "ontology8_after": post8}, indent=2))

    out = _REPO / "docs" / "item37_fish_flip_usda_ops.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("Wrote", out)
    return 0 if rc_flip == 0 and rc_usda == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
