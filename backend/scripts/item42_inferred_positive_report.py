#!/usr/bin/env python3
"""Item 42 report: *_inferred uncertainty softens triggered allergen FAIL → UNCERTAIN.

Mechanism (given Item 34): Item 34 stopped knowledge_state from demoting triggered
FAIL. The untrusted gate in ``_verdict_for`` still runs first — any uncertainty
flag containing ``inferred`` makes ``is_trusted_for_compliance`` false for DB
rows, so triggered allergy FAIL never stands.
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

from core.external_apis.usda_fdc import _FISH_NAME, _SHELLFISH_NAME
from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.knowledge.ingredient_db import get_supabase_config
from core.normalization.normalizer import normalize_ingredient_key
from supabase import create_client

ALLERGEN_FLAGS = (
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
)

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

_LAND_MEAT = re.compile(
    r"\b(beef|pork|lamb|goat|sheep|chicken|turkey|duck|veal|mutton|bison|"
    r"venison|bacon|ham|meat|poultry|liver|steak|sausage|emu|ostrich|"
    r"alligator|kangaroo|rabbit)\b",
    re.I,
)
_PLANT_DAIRY_OVERRIDE = re.compile(
    r"\b(almond|oat|soy|soya|rice|coconut|hemp|cashew|pea)\s+(milk|yogurt|yoghurt|cheese|cream|butter)\b",
    re.I,
)


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
                "canonical_name,source,knowledge_state,uncertainty_flags,"
                "animal_origin,animal_species,"
                + ",".join(ALLERGEN_FLAGS)
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


def _inferred_tokens(unc) -> list[str]:
    return [str(x) for x in (unc or []) if "inferred" in str(x).lower()]


def _prod_flag(name: str, flag: str) -> dict:
    rid = FLAG_TO_RID[flag]
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
        "restriction": rid,
        "verdict": v,
        "layer": getattr(r, "resolution_layer", None),
        "trusted": bool(getattr(r, "trusted", False)),
        "flag_on_ci": bool(ci.flags.get(flag)),
    }


def _fish_evidence_class(name: str) -> str:
    """Split without raw foodCategory: name lexicon vs category-only residue."""
    n = name.lower()
    shell = bool(_SHELLFISH_NAME.search(n))
    fish = bool(_FISH_NAME.search(n)) or bool(re.search(r"\bseafood\b", n))
    if shell or fish:
        return "name_sniffed"
    return "category_or_other_no_name_match"


def _hand_rate(name: str, flag: str, source: str) -> str:
    """Heuristic precision label for the sample (not a gold label)."""
    n = name.lower()
    if flag == "fish_source":
        if _LAND_MEAT.search(n) and not _FISH_NAME.search(n):
            return "likely_false"
        if _FISH_NAME.search(n) or "seafood" in n or n.startswith("fish "):
            return "likely_true"
        if "finfish" in n or "shellfish" in n:
            return "likely_true"
        return "needs_human"
    if flag == "shellfish_source":
        if _SHELLFISH_NAME.search(n) or "seafood" in n:
            return "likely_true"
        if _LAND_MEAT.search(n):
            return "likely_false"
        return "needs_human"
    if flag == "dairy_source":
        if _PLANT_DAIRY_OVERRIDE.search(n):
            return "likely_false"
        if re.search(
            r"\b(milk|cheese|butter|cream|whey|yogurt|yoghurt|ghee|dairy|"
            r"casein|lactose|buttermilk|paneer|curd)\b",
            n,
        ):
            return "likely_true"
        return "needs_human"
    if flag == "egg_source":
        if "eggplant" in n or "egg free" in n or "egg-free" in n:
            return "likely_false"
        if re.search(r"\b(egg|eggs)\b", n):
            return "likely_true"
        return "needs_human"
    if flag == "gluten_source":
        if re.search(r"\b(wheat|barley|rye|gluten|spelt|einkorn|khorasan)\b", n):
            return "likely_true"
        if "oat" in n:
            return "needs_human"  # the oat bug class
        return "needs_human"
    return "needs_human"


def main() -> int:
    random.seed(42)
    c = _client()
    live = _page(c)

    hits = []
    for g in live:
        inferred = _inferred_tokens(g.get("uncertainty_flags"))
        if not inferred:
            continue
        trues = [f for f in ALLERGEN_FLAGS if g.get(f)]
        if not trues:
            # also species-as-allergen proxy
            sp = (g.get("animal_species") or "").lower()
            if sp in ("fish", "shellfish"):
                trues = ["fish_source" if sp == "fish" else "shellfish_source"]
            else:
                continue
        for f in trues:
            hits.append(
                {
                    "canonical_name": g["canonical_name"],
                    "source": g.get("source") or "?",
                    "flag": f,
                    "inferred": inferred,
                    "knowledge_state": g.get("knowledge_state"),
                    "animal_species": g.get("animal_species"),
                }
            )

    by_src_flag = Counter((h["source"], h["flag"]) for h in hits)
    by_src = Counter(h["source"] for h in hits)
    by_inferred_token = Counter(t for h in hits for t in h["inferred"])

    # Verdict today for each hit (dedupe name+flag)
    verdict_counts = Counter()
    soft_fail = []  # flag true on CI, verdict UNCERTAIN, untrusted
    samples_by_src: dict[str, list] = defaultdict(list)

    # Deduplicate name+flag for probing
    seen = set()
    unique_hits = []
    for h in hits:
        key = (normalize_ingredient_key(h["canonical_name"]), h["flag"])
        if key in seen:
            continue
        seen.add(key)
        unique_hits.append(h)

    for h in unique_hits:
        probe = _prod_flag(h["canonical_name"], h["flag"])
        h["probe"] = probe
        verdict_counts[(h["source"], h["flag"], probe["verdict"])] += 1
        if (
            probe["flag_on_ci"]
            and probe["verdict"] == "UNCERTAIN"
            and not probe["trusted"]
        ):
            soft_fail.append(h)
        samples_by_src[h["source"]].append(h)

    # Hand-check 50 per source (or all if fewer)
    hand = {}
    for src, rows in samples_by_src.items():
        take = rows[:]
        random.shuffle(take)
        take = take[:50]
        rated = []
        for h in take:
            label = _hand_rate(h["canonical_name"], h["flag"], src)
            evidence = None
            if h["flag"] in ("fish_source", "shellfish_source") and src == "usda":
                evidence = _fish_evidence_class(h["canonical_name"])
            rated.append(
                {
                    "canonical_name": h["canonical_name"],
                    "flag": h["flag"],
                    "precision_guess": label,
                    "evidence_class": evidence,
                    "verdict_today": h["probe"]["verdict"],
                    "layer": h["probe"]["layer"],
                }
            )
        hand[src] = {
            "n_sampled": len(rated),
            "precision_guess_counts": dict(Counter(r["precision_guess"] for r in rated)),
            "evidence_class_counts": dict(
                Counter(r["evidence_class"] for r in rated if r["evidence_class"])
            ),
            "rows": rated,
        }

    # USDA fish/shellfish evidence split across ALL usda fish hits (not just sample)
    usda_fish = [
        h
        for h in unique_hits
        if h["source"] == "usda" and h["flag"] in ("fish_source", "shellfish_source")
    ]
    usda_evidence = Counter(_fish_evidence_class(h["canonical_name"]) for h in usda_fish)

    # Mechanism note via trust helper
    mech = {
        "item34": (
            "Item 34: triggered FAIL stands despite low knowledge_state. "
            "That path is never reached when trusted=False."
        ),
        "trusted_gate": (
            "resolution_trust.is_trusted_for_compliance: any uncertainty flag "
            "containing 'inferred' ⇒ trusted=False for non-static sources. "
            "_verdict_for returns UNCERTAIN before the FAIL/Item-34 branch."
        ),
        "static_exception": (
            "L1/L2 (source=static) are always trusted, so the same inferred "
            "token on an ontology/truth-anchor row would not soften FAIL — "
            "the trap is L3 DB rows."
        ),
        "demo": {
            "name": "fish cod atlantic cooked dry heat",
            "probe": _prod_flag("fish cod atlantic cooked dry heat", "fish_source"),
        },
    }

    policy = {
        "recommended": "inferred_caps_safe_only_for_allergy_medical",
        "detail": [
            "For allergy + medical restrictions: a triggered positive allergen "
            "flag must stand as FAIL even when uncertainty_flags contain "
            "*_inferred (Item 34 symmetry). The untrusted gate should not "
            "demote triggered FAIL.",
            "Keep *_inferred as a SAFE ceiling (clean pass → UNCERTAIN/WARN) "
            "so bad negatives cannot mint firm SAFE.",
            "Split markers: category-derived fish/shellfish (FDC foodCategory "
            "'Finfish and Shellfish Products') is stronger evidence than a "
            "name sniff — prefer a distinct token "
            "(e.g. usda_fdc_category_derived) that does not trip the blanket "
            "inferred untrusted gate, OR treat category-derived as asserted "
            "without inferred.",
            "Name-sniffed allergen flags may keep a weaker marker but still "
            "must not silence FAIL for allergy/medical once the flag is true.",
            "Counterweight: measure precision before shipping. Prior USDA "
            "dairy_implies_animal contradictions (136) show name/category "
            "inference can false-Avoid; the hand sample below is the first cut.",
        ],
        "rejected": {
            "leave_as_is": "128/216 fish-shaped names stay UNCERTAIN with true fish flags — same harm class as the oat Item-34 bug.",
            "drop_inferred_entirely": "Loses the SAFE ceiling that blocks firm SAFE on weak rows.",
        },
    }

    report = {
        "n_live_groups_scanned": len(live),
        "n_allergen_true_plus_inferred_pairs": len(hits),
        "n_unique_name_flag": len(unique_hits),
        "by_source": dict(by_src),
        "by_source_flag": {
            f"{s}|{f}": n for (s, f), n in sorted(by_src_flag.items(), key=lambda x: -x[1])
        },
        "by_inferred_token": dict(by_inferred_token),
        "verdict_counts_by_source_flag": {
            f"{s}|{f}|{v}": n
            for (s, f, v), n in sorted(verdict_counts.items(), key=lambda x: -x[1])
        },
        "softened_fail_count": len(soft_fail),
        "softened_fail_by_source": dict(Counter(h["source"] for h in soft_fail)),
        "usda_fish_shellfish_evidence_split": dict(usda_evidence),
        "hand_check_50_per_source": {
            s: {k: v for k, v in meta.items() if k != "rows"}
            for s, meta in hand.items()
        },
        "hand_check_samples": hand,
        "mechanism": mech,
        "policy": policy,
    }

    out = _REPO / "docs" / "item42_inferred_positive_uncertainty.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# Item 42 — Inferred positives softened to UNCERTAIN (report)",
        "",
        "**Status:** opened 2026-10-13 (report first; no code)  ",
        "**Priority:** P0  ",
        "**Companion:** Item **34** · `resolution_trust.py` · `compliance._verdict_for` · tracker row **42**",
        "",
        "## Mechanism (Item 34 path, different gate)",
        "",
        mech["item34"],
        "",
        mech["trusted_gate"],
        "",
        mech["static_exception"],
        "",
        f"Demo `{mech['demo']['name']}`: {mech['demo']['probe']}",
        "",
        "## Live exposure",
        "",
        f"- Groups scanned: **{len(live)}**",
        f"- Allergen-true × `*_inferred` pairs: **{len(hits)}** "
        f"({len(unique_hits)} unique name×flag)",
        f"- Softened FAIL (flag on CI, untrusted, UNCERTAIN): **{len(soft_fail)}**",
        "",
        "### By source",
        "",
    ]
    for s, n in by_src.most_common():
        lines.append(f"- `{s}`: {n}")
    lines += ["", "### By source × flag (top)", ""]
    for (s, f), n in by_src_flag.most_common(25):
        lines.append(f"- `{s}` / `{f}`: {n}")
    lines += ["", "### Verdicts today (source × flag × verdict)", ""]
    for (s, f, v), n in verdict_counts.most_common(30):
        lines.append(f"- `{s}` / `{f}` → **{v}**: {n}")
    lines += [
        "",
        "### USDA fish/shellfish evidence split (no raw foodCategory on Layer-1)",
        "",
        f"{dict(usda_evidence)}",
        "",
        "`name_sniffed` = fish/shellfish lexicon hits the canonical name. "
        "`category_or_other_no_name_match` = flag true without a name hit "
        "(the FDC `Finfish and Shellfish Products` path, or other non-name route).",
        "",
        "## Hand-check (≤50 per source, heuristic)",
        "",
    ]
    for src, meta in sorted(hand.items()):
        lines.append(
            f"- **{src}** (n={meta['n_sampled']}): {meta['precision_guess_counts']}"
            + (
                f" evidence={meta['evidence_class_counts']}"
                if meta.get("evidence_class_counts")
                else ""
            )
        )
    lines += [
        "",
        "## Policy recommendation",
        "",
        f"**{policy['recommended']}**",
        "",
    ]
    for d in policy["detail"]:
        lines.append(f"- {d}")
    lines += [
        "",
        "Artifact: `docs/item42_inferred_positive_uncertainty.json`.",
    ]
    md = _REPO / "docs" / "item42_inferred_positive_uncertainty.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "pairs": len(hits),
                "unique": len(unique_hits),
                "softened": len(soft_fail),
                "by_source": dict(by_src),
                "usda_evidence": dict(usda_evidence),
                "hand": {s: meta["precision_guess_counts"] for s, meta in hand.items()},
                "wrote": [str(out), str(md)],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
