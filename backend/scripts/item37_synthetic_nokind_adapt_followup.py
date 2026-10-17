#!/usr/bin/env python3
"""Item 37 follow-up: minimal synthetic restore, animal no-kind split-match,
COMPUTED_OK/FINDING rules printout.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS
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

# Lexicon tokens for USDA no-kind scan (fish/shellfish signals in English names).
_FISH_LEX = re.compile(
    r"\b(fish|seafood|snapper|tuna|salmon|cod|haddock|halibut|mackerel|sardine|sardines|"
    r"anchovy|anchovies|trout|bass|perch|pike|carp|eel|herring|swordfish|tilapia|"
    r"catfish|grouper|pomfret|hilsa|rohu|katla|seer|bombay duck|trevally|barramundi|"
    r"mullet|whiting|pollock|sole|flounder|sturgeon|caviar|roe|surimi|sprat|sprats)\b",
    re.I,
)
_SHELL_LEX = re.compile(
    r"\b(shrimp|prawn|crab|lobster|crawfish|crayfish|clam|mussel|oyster|scallop|"
    r"squid|octopus|cuttlefish|shellfish|crustacean|mollusk|mollusc)\b",
    re.I,
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


def _phase1_synthetic_names() -> list[str]:
    md = (_REPO / "docs" / "item11_phase1_flag_changes.md").read_text()
    names = []
    for m in re.finditer(r"^- `([^`]+)` — added: ([^\n]+)", md, re.M):
        name, rest = m.group(1), m.group(2)
        if "synthetic false→true" in rest or "synthetic false->true" in rest:
            names.append(normalize_ingredient_key(name))
    return sorted(set(names))


def synthetic_rules_audit() -> dict:
    """Does any restriction rule / seeded path read the synthetic boolean?"""
    seeded = rules_module.RULE_SEED
    rule_hits = [r for r in seeded if r.get("field") == "synthetic"]
    # VALID_FLAG_COLUMNS lists synthetic as a legal column, not a used trigger.
    return {
        "in_VALID_FLAG_COLUMNS": "synthetic" in rules_module.VALID_FLAG_COLUMNS,
        "RULE_SEED_trigger_hits": rule_hits,
        "reads_synthetic_boolean": len(rule_hits) > 0,
        "note": (
            "No seeded restriction triggers on synthetic. uncertainty_flags text "
            "like may_be_synthetic_* is separate from the boolean column. "
            "verdict_cap paths do not key off synthetic."
        ),
    }


def minimal_synthetic_restore(c) -> dict:
    """Restore dump synthetic=true unasserted; keep AUTO; drop asserted false."""
    names = _phase1_synthetic_names()
    rows_out = []
    for name in names:
        live = (
            c.table("ike2_ingredient_groups")
            .select("*")
            .eq("canonical_name", name)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not live:
            rows_out.append(
                {
                    "canonical_name": name,
                    "status": "missing",
                    "evidence": "phase1 FSSAI synthetic false→true demotion; no live row",
                }
            )
            continue
        g = live[0]
        before_syn = bool(g.get("synthetic"))
        before_af = list(g.get("asserted_flags") or [])
        before_ks = g.get("knowledge_state")
        # Dump value was synthetic=true (FSSAI). Leave it unasserted.
        # Drop synthetic from asserts; keep other true-only asserts.
        after_af = [f for f in before_af if f != "synthetic" and g.get(f)]
        patch = {
            "synthetic": True,  # dump value (FSSAI), unasserted
            "asserted_flags": after_af,
            "knowledge_state": "AUTO_CLASSIFIED",
        }
        c.table("ike2_ingredient_groups").update(patch).eq("id", g["id"]).execute()
        after = (
            c.table("ike2_ingredient_groups")
            .select("synthetic,asserted_flags,knowledge_state,uncertainty_flags")
            .eq("id", g["id"])
            .limit(1)
            .execute()
            .data[0]
        )
        rows_out.append(
            {
                "canonical_name": name,
                "before": {
                    "synthetic": before_syn,
                    "asserted_flags": before_af,
                    "knowledge_state": before_ks,
                },
                "after": {
                    "synthetic": after.get("synthetic"),
                    "asserted_flags": after.get("asserted_flags"),
                    "knowledge_state": after.get("knowledge_state"),
                    "uncertainty_flags": after.get("uncertainty_flags"),
                },
                "evidence": (
                    "blanket Phase-1 demotion restore was asserted synthetic=false "
                    "without per-row evidence; nothing reads synthetic; "
                    "minimal form: dump synthetic=true unasserted + AUTO_CLASSIFIED"
                ),
            }
        )
    # highlight requested rows
    focus = {
        n: next((r for r in rows_out if r["canonical_name"] == n), None)
        for n in ("canthaxanthin", "polyglycerol esters of fatty acids")
    }
    return {
        "rules_audit": synthetic_rules_audit(),
        "restored_count": sum(1 for r in rows_out if r.get("status") != "missing"),
        "missing_count": sum(1 for r in rows_out if r.get("status") == "missing"),
        "rows": rows_out,
        "focus": focus,
    }


# Single-token generics that appear inside fish aliases but must not match
# land-meat no-kind rows (liver→cod liver, meat→albacore tuna, …).
_ALIAS_STOP = frozenset({
    "meat", "fish", "raw", "cooked", "dried", "fresh", "frozen", "skin",
    "skinless", "with", "without", "leg", "legs", "round", "small", "large",
    "liver", "oil", "roe", "steak", "fillet", "fillets", "whole", "mixed",
    "species", "tongue", "breast", "thigh", "wing", "heart", "brain",
    "intestine", "stomach", "fat", "bones", "head", "tail", "farmed", "wild",
})


def _split_alias_parts(alias: str) -> list[str]:
    """Split bundled INFOODS-style alias strings into common names / binomials.

    Phrase-level only (comma/semicolon/aka separators). Does not emit bare
    tokens — that produced false hits (meat→tuna, liver→cod liver).
    """
    raw = (alias or "").strip()
    if not raw:
        return []
    parts = re.split(r"[,;/|]+|\s+aka\s+", raw, flags=re.I)
    out = []
    for p in parts:
        p = p.strip().strip(".")
        if not p or len(p) < 3:
            continue
        p = re.sub(r"^[A-Za-z]{1,4}\.\s+", "", p).strip()
        key = normalize_ingredient_key(p)
        if not key or key in _ALIAS_STOP:
            continue
        words = key.split()
        # Reject single-token generics; keep multi-word commons and binomials.
        if len(words) == 1 and (key in _ALIAS_STOP or len(key) < 5):
            continue
        out.append(key)
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def infoods_alias_index(c) -> dict[str, str]:
    """Map individual alias parts → live INFOODS fish/shellfish canonical."""
    infoods = [
        g
        for g in _page(c, source="infoods")
        if g.get("fish_source") or g.get("shellfish_source")
    ]
    idx: dict[str, str] = {}
    for g in infoods:
        canon = g["canonical_name"]
        keys = set(_split_alias_parts(canon))
        keys.add(normalize_ingredient_key(canon))
        sp = str(g.get("animal_species") or "").strip()
        if sp:
            keys.update(_split_alias_parts(sp))
        ings = (
            c.table("ike2_ingredients")
            .select("id,normalized_name")
            .eq("group_id", g["id"])
            .execute()
            .data
            or []
        )
        for ing in ings:
            keys.add(normalize_ingredient_key(ing.get("normalized_name") or ""))
            als = (
                c.table("ike2_aliases")
                .select("normalized_alias")
                .eq("ingredient_id", ing["id"])
                .execute()
                .data
                or []
            )
            for a in als:
                keys.update(_split_alias_parts(a.get("normalized_alias") or ""))
        for k in keys:
            if k and k not in idx:
                idx[k] = canon
    return idx


def animal_nokind_report(c) -> dict:
    live = _page(c)
    no_kind = [
        g
        for g in live
        if g.get("animal_origin") and not any(g.get(f) for f in KIND_FLAGS)
    ]
    idx = infoods_alias_index(c)
    # Inverted index: multi-word INFOODS parts for token-subset matching.
    multi_parts: list[tuple[str, frozenset[str], str]] = []
    for part, canon in idx.items():
        words = frozenset(part.split())
        if len(words) >= 2:
            multi_parts.append((part, words, canon))

    matched = []
    unmatched = []
    for g in no_kind:
        key = normalize_ingredient_key(g.get("canonical_name") or "")
        key_words = frozenset(key.split())
        hit = None
        hit_part = None
        how = None
        # 1) Exact equality against an INFOODS individual common/binomial.
        if key in idx:
            hit, hit_part, how = idx[key], key, "exact"
        else:
            for p in _split_alias_parts(g.get("canonical_name") or ""):
                if p in idx:
                    hit, hit_part, how = idx[p], p, "exact_part"
                    break
        # 2) Multi-word INFOODS phrase whose tokens are all present in the live name
        #    (order-independent): "dungeness crab" ⊆ "crustaceans crab dungeness raw".
        if not hit:
            best = None
            for part, words, canon in multi_parts:
                if words <= key_words and (best is None or len(words) > len(best[1])):
                    best = (part, words, canon)
            if best:
                hit, hit_part, how = best[2], best[0], "token_subset"
        if hit:
            matched.append(
                {
                    "live": g["canonical_name"],
                    "source": g.get("source"),
                    "matched_part": hit_part or key,
                    "infoods": hit,
                    "how": how,
                }
            )
        else:
            unmatched.append(g)

    by_src = Counter(g.get("source") or "?" for g in no_kind)
    ont = [g for g in unmatched if g.get("source") == "ontology"]
    ifct = [g for g in unmatched if g.get("source") == "ifct"]
    usda = [g for g in unmatched if g.get("source") == "usda"]

    def _hand_tag(name: str) -> str:
        nl = name.lower()
        if _SHELL_LEX.search(nl) and "oyster mushroom" not in nl:
            return "shellfish_suspect"
        if _FISH_LEX.search(nl):
            return "fish_suspect"
        if re.search(
            r"\b(beef|pork|lamb|goat|sheep|chicken|turkey|duck|meat|bacon|"
            r"ham|veal|mutton|bison|venison|liver|heart|kidney|tripe|brain)\b",
            nl,
        ):
            return "land_meat"
        if re.search(r"\b(egg|eggs)\b", nl) and "eggplant" not in nl:
            return "egg_suspect"
        if re.search(r"\b(milk|cheese|butter|cream|whey|yogurt|ghee)\b", nl):
            return "dairy_suspect"
        return "other_animal"

    ont_read = [
        {"canonical_name": g["canonical_name"], "tag": _hand_tag(g["canonical_name"])}
        for g in sorted(ont, key=lambda x: x["canonical_name"])
    ]
    ifct_read = [
        {"canonical_name": g["canonical_name"], "tag": _hand_tag(g["canonical_name"])}
        for g in sorted(ifct, key=lambda x: x["canonical_name"])
    ]
    usda_lex = []
    for g in usda:
        tag = _hand_tag(g["canonical_name"])
        if tag in ("fish_suspect", "shellfish_suspect"):
            usda_lex.append({"canonical_name": g["canonical_name"], "tag": tag})

    return {
        "animal_no_kind": len(no_kind),
        "by_source": dict(by_src),
        "infoods_index_keys": len(idx),
        "matched_via_split_alias": matched,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "ontology_hand_read": ont_read,
        "ontology_tag_counts": dict(Counter(r["tag"] for r in ont_read)),
        "ifct_hand_read": ifct_read,
        "ifct_tag_counts": dict(Counter(r["tag"] for r in ifct_read)),
        "usda_fish_shellfish_lexicon_hits": usda_lex,
        "usda_lexicon_hit_count": len(usda_lex),
        "finding_rules": FINDING_RULES_DOC,
    }


FINDING_RULES_DOC = {
    "scope": "SAFE↔UNCERTAIN orthographic pairs only (not SAFE↔NOT_SAFE)",
    "COMPUTED_OK": (
        "SAFE-side resolve + flag snapshot shows no matching species-allergen "
        "identity for the restriction under test. Cross-species SAFE is OK "
        "(e.g. fish under shellfish_allergy when shellfish_source is false)."
    ),
    "FINDING_fish_allergy": [
        "SAFE under fish_allergy AND (fish_source OR animal_species fish*)",
        "SAFE under fish_allergy AND animal_origin=true AND no kind flag "
        "(fish/shellfish/dairy/egg/insect/bee) — unflagged-fish shape; YES this is a FINDING",
    ],
    "FINDING_shellfish_allergy": [
        "SAFE under shellfish_allergy AND (shellfish_source OR animal_species contains shellfish)",
        "animal_origin alone under shellfish_allergy is NOT a FINDING (fish≠shellfish)",
    ],
    "FINDING_other_allergens": (
        "SAFE under egg_free/dairy_free/peanut/tree_nut/soy/sesame/mustard/celery/lupin "
        "AND the matching *_source flag is true on the SAFE side"
    ),
    "animal_no_kind_under_species_allergen_is_finding": {
        "fish_allergy": True,
        "shellfish_allergy": False,
        "rationale": (
            "Unflagged animal under fish_allergy is the snapper/trevally underflag shape. "
            "Under shellfish_allergy, bare animal_origin without shellfish_source is not "
            "enough — most no-kind animals are land meat."
        ),
    },
}


def main() -> int:
    c = _client()
    report: dict = {}

    print("=== 1 synthetic rules + minimal restore ===", flush=True)
    syn = minimal_synthetic_restore(c)
    report["1_synthetic"] = syn
    print(
        json.dumps(
            {
                "rules": syn["rules_audit"],
                "restored": syn["restored_count"],
                "focus": syn["focus"],
            },
            indent=2,
        )
    )

    print("=== 2 animal no-kind split-match ===", flush=True)
    nok = animal_nokind_report(c)
    report["2_animal_nokind"] = nok
    print(
        json.dumps(
            {
                "animal_no_kind": nok["animal_no_kind"],
                "matched_count": nok["matched_count"],
                "matched_sample": nok["matched_via_split_alias"][:30],
                "ontology_tag_counts": nok["ontology_tag_counts"],
                "ifct_tag_counts": nok["ifct_tag_counts"],
                "usda_lexicon_hit_count": nok["usda_lexicon_hit_count"],
                "usda_lexicon_sample": nok["usda_fish_shellfish_lexicon_hits"][:40],
                "finding_rules": nok["finding_rules"],
            },
            indent=2,
        )
    )

    out = _REPO / "docs" / "item37_synthetic_nokind_adapt_followup.json"
    # trim huge lists in the on-disk report but keep hand reads
    slim = {
        "1_synthetic": {
            "rules_audit": syn["rules_audit"],
            "restored_count": syn["restored_count"],
            "missing_count": syn["missing_count"],
            "focus": syn["focus"],
            "rows": syn["rows"],
        },
        "2_animal_nokind": {
            k: nok[k]
            for k in nok
            if k
            not in (
                # keep hand reads; drop only if enormous — keep all for audit
            )
        },
        "3_adapt": {
            "change": "map_record asserts trues only unless curated asserted_flags present",
            "tripwire": "asserted_flags_false_pollution remains second line",
        },
    }
    out.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print("Wrote", out)

    # also rewrite unmatched with tags for ontology/ifct
    (_REPO / "docs" / "item37_animal_no_kind_hand_read.json").write_text(
        json.dumps(
            {
                "ontology": nok["ontology_hand_read"],
                "ifct": nok["ifct_hand_read"],
                "usda_fish_shellfish_lexicon": nok["usda_fish_shellfish_lexicon_hits"],
                "infoods_split_matches": nok["matched_via_split_alias"],
            },
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
