#!/usr/bin/env python3
"""Item 12 — first scheduled task: wrap existing one-off IKE-2 audits.

Runs report-only (no writes). Exit 1 if any audit reports a blocking finding
when ``--fail-on-findings`` is set.

Audits:
  1. asserted-false signature (full-block pollution reappearance)
  2. DISCOVERED name inventory (count + sample; optional diff vs prior JSON)
  3. L2 ↔ L3 drift by name (live_true && l2_false on verdict-relevant flags)
  4. lexicon vs verdict over live groups (SAFE with name-implied flag absent,
     excluding enumerated false friends)

Usage (from backend/):
  python scripts/ike2_item12_scheduled_audits.py
  python scripts/ike2_item12_scheduled_audits.py --fail-on-findings
"""
from __future__ import annotations

import argparse
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

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology as lo
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

VERDICT_FLAGS = tuple(FLAG_TO_RID) + ("animal_origin",)

FAMILY_LEX = {
    "shellfish_source": re.compile(
        r"\b(prawns?|shrimps?|crabs?|lobsters?|crawfish|crayfish|langoustines?|"
        r"krill|yabb(?:y|ies)|mussels?|oysters?|clams?|scallops?|squids?|"
        r"octopuses?|octopus|cuttlefish|shellfish|molluscs?|mollusks?|"
        r"crustaceans?)\b",
        re.I,
    ),
    "fish_source": re.compile(
        r"\b(fish|finfish|salmon|tuna|cod|haddock|halibut|mackerel|sardine|"
        r"anchovy|trout|bass|tilapia|catfish|pollock|surimi|roe|caviar)\b",
        re.I,
    ),
    "dairy_source": re.compile(
        r"\b(milk|cheese|whey|cream|butter|dairy|lactose|casein|yogurt|"
        r"yoghurt|buttermilk|paneer|ghee|dahi|curd|khoa|mawa|lassi|chaas|"
        r"malai)\b",
        re.I,
    ),
    "egg_source": re.compile(
        r"\b(eggs?|eggnog|mayonnaise|meringue|anda)\b", re.I
    ),
    "gluten_source": re.compile(
        r"\b(wheat|barley|rye|gluten|bread|atta|maida|semolina|sooji|suji|"
        r"rava|dalia|chapatti|chapati|roti|paratha|naan|puri)\b",
        re.I,
    ),
    "soy_source": re.compile(
        r"\b(soy|soya|soybean|tofu|tempeh|edamame)\b", re.I
    ),
    "tree_nut_source": re.compile(
        r"\b(almonds?|walnuts?|pecans?|cashews?|pistachios?|hazelnuts?|"
        r"filberts?|macadamias?|brazil\s*nuts?|pine\s*nuts?|pinenuts?|"
        r"chestnuts?|pralines?|marzipan|nougat|gianduja|frangipane|"
        r"amaretto|pesto|kaju|badam|pista|akhrot)\b",
        re.I,
    ),
    "sesame_source": re.compile(r"\b(sesame|til)\b", re.I),
    "mustard_source": re.compile(r"\b(mustard|rai|sarson)\b", re.I),
}


def _client():
    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured")
    return create_client(cfg.url, cfg.key)


def _page_groups(c):
    out = []
    start = 0
    while True:
        batch = (
            c.table("ike2_ingredient_groups")
            .select("*")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        out.extend(batch)
        if len(batch) < 1000:
            break
        start += 1000
    return out


def audit_asserted_false_signature(groups: list[dict]) -> dict:
    """Same invariant as validate: unreviewed asserted false, or >3 backstop."""
    from core.knowledge.ike2.etl.validate import validate_rows

    polluted = []
    for g in groups:
        row = dict(g)
        # Live groups lack the stem-triage escape marker; audit shares validate.
        ok, rejects = validate_rows([row])
        if rejects:
            violated = rejects[0].get("violated_constraint")
            if violated in (
                "asserted_flags_unreviewed_negative",
                "asserted_flags_false_pollution",
            ):
                af = g.get("asserted_flags") or []
                falses = [f for f in af if f in BOOL_FLAGS and not g.get(f)]
                polluted.append(
                    {
                        "canonical_name": g.get("canonical_name"),
                        "source": g.get("source"),
                        "n_asserted_false": len(falses),
                        "violated_constraint": violated,
                    }
                )
    return {
        "audit": "asserted_false_signature",
        "polluted_rows": len(polluted),
        "sample": polluted[:40],
        "blocking": len(polluted) > 0,
    }


def audit_discovered_names(groups: list[dict], prior_path: Path | None) -> dict:
    names = sorted(
        g["canonical_name"]
        for g in groups
        if g.get("knowledge_state") == "DISCOVERED" and g.get("canonical_name")
    )
    prior = []
    if prior_path and prior_path.exists():
        prior = json.loads(prior_path.read_text()).get("discovered_names") or []
    prior_set = set(prior)
    cur_set = set(names)
    return {
        "audit": "discovered_name_diff",
        "count": len(names),
        "added": sorted(cur_set - prior_set)[:50],
        "removed": sorted(prior_set - cur_set)[:50],
        "sample": names[:40],
        "blocking": False,
    }


def audit_l2_l3_drift(groups: list[dict]) -> dict:
    lo.reset_cache()
    drifted = []
    for g in groups:
        name = g.get("canonical_name") or ""
        norm = normalize_ingredient_key(name)
        fact = lo.lookup(norm)
        if fact is None:
            continue
        l2 = dict(fact.flags)
        diffs = [
            f
            for f in VERDICT_FLAGS
            if g.get(f) and not l2.get(f)
        ]
        if diffs:
            drifted.append(
                {
                    "canonical_name": name,
                    "source": g.get("source"),
                    "live_true_l2_false": diffs,
                }
            )
    return {
        "audit": "l2_l3_drift_by_name",
        "names_with_drift": len(drifted),
        "sample": drifted[:40],
        "blocking": len(drifted) > 0,
    }


def _false_friends() -> set[tuple[str, str]]:
    path = _REPO / "data" / "lexicon_scan_false_friends.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text())
    return {
        (normalize_ingredient_key(r["name"]), r["flag"])
        for r in (data.get("false_friends") or [])
    }


def audit_lexicon_vs_verdict(groups: list[dict]) -> dict:
    ff = _false_friends()
    safes = []
    for g in groups:
        name = g.get("canonical_name") or ""
        norm = normalize_ingredient_key(name)
        for flag, lex in FAMILY_LEX.items():
            if not lex.search(name):
                continue
            if (norm, flag) in ff:
                continue
            if g.get(flag):
                continue
            rid = FLAG_TO_RID[flag]
            cache.clear()
            r = resolve(name, None)
            ci = to_compliance_input(r, query_atom=name)
            if ci.flags.get(flag):
                continue
            v = to_external(
                evaluate(
                    [ci],
                    SimpleNamespace(restrictions={rid: "medical"}),
                    rules_module.seeded_rules(),
                ).verdict
            )
            if v == "SAFE":
                safes.append(
                    {
                        "canonical_name": name,
                        "flag": flag,
                        "layer": r.resolution_layer,
                        "trusted": bool(ci.trusted),
                        "source": g.get("source"),
                    }
                )
    return {
        "audit": "lexicon_vs_verdict_live",
        "safe_with_name_implied_flag_absent": len(safes),
        "by_flag": dict(Counter(s["flag"] for s in safes)),
        "sample": safes[:60],
        "blocking": len(safes) > 0,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="exit 1 when any audit sets blocking=True",
    )
    ap.add_argument(
        "--out",
        default=str(
            _BACKEND / ".local_reports" / "item12_scheduled_audit_report.json"
        ),
    )
    ap.add_argument(
        "--discovered-prior",
        default="",
        help="optional prior JSON with discovered_names for diff",
    )
    args = ap.parse_args(argv)

    c = _client()
    groups = _page_groups(c)
    report = {
        "live_groups": len(groups),
        "audits": [
            audit_asserted_false_signature(groups),
            audit_discovered_names(
                groups,
                Path(args.discovered_prior) if args.discovered_prior else None,
            ),
            audit_l2_l3_drift(groups),
            audit_lexicon_vs_verdict(groups),
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({a["audit"]: {k: a[k] for k in a if k != "sample"} for a in report["audits"]}, indent=2))
    print(f"wrote {out}")
    if args.fail_on_findings and any(a.get("blocking") for a in report["audits"]):
        return 1
    from core.knowledge.ike2.audit_health import record_live_audit_success

    record_live_audit_success(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
