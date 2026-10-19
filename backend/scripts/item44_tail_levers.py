#!/usr/bin/env python3
"""Report-only: coverage uplift on instances beyond K=1152 from three levers.

Levers (applied independently to L5-unknown held-out instances not covered by
the top-K=1152 frequency promotion set):
  (a) modifier stripping — organic/natural/dried/…/country suffixes
  (b) OFF taxonomy synonyms
  (c) OFF ancestry to a class with a known hazard profile

Writes ``backend/.local_reports/item44_tail_levers.json``.
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
sys.path.insert(0, str(_BACKEND / "scripts"))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.normalization.parser import flatten_ingredients
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG, hazard_hits_in_text
from item44_label_benchmark import _IDS_PATH, _layer_bucket
from item44_pilot_evidence import (
    _FREQ_PATH,
    _FREQ_PROGRESS,
    _PRODUCT_CACHE,
    _RESOLVE_MEMO,
    _load_product_cache,
    _resolve_atom,
    accumulate_freq_from_ids,
    load_off_taxonomy,
)
from core.knowledge.ike2.resolver import resolve

_OUT = _BACKEND / ".local_reports" / "item44_tail_levers.json"
_K = 1152

_MODIFIERS = re.compile(
    r"^(?:organic|natural|dried|dry|ground|powdered|powder|concentrate|concentrated|"
    r"extract\s+of|pure|fresh|raw|whole|refined|unbleached|bleached|enriched|"
    r"iodised|iodized|fortified)\s+",
    re.I,
)
_COUNTRY_SUFFIX = re.compile(
    r"\s+\((?:usa|uk|eu|india|france|germany|italy|spain|china|japan|mexico|"
    r"canada|australia|brazil|product of [^)]+)\)\s*$",
    re.I,
)
_EXTRACT_OF = re.compile(r"^extract\s+of\s+", re.I)


def _strip_modifiers(atom: str) -> str:
    a = (atom or "").strip()
    a = _COUNTRY_SUFFIX.sub("", a).strip()
    prev = None
    while prev != a:
        prev = a
        a = _MODIFIERS.sub("", a).strip()
        a = _EXTRACT_OF.sub("", a).strip()
    return a


def _cache_by_code() -> dict[str, dict]:
    _load_product_cache()
    by = {}
    for k, v in _PRODUCT_CACHE.items():
        if not v:
            continue
        code = str(v.get("code") or k.split("|", 1)[0])
        if code and (v.get("ingredients_text") or "").strip():
            by[code] = v
    return by


def _taxonomy_synonyms(taxonomy: dict) -> dict[str, str]:
    """Map synonym surface -> primary OFF id / name (lowercase)."""
    out: dict[str, str] = {}
    if not isinstance(taxonomy, dict):
        return out
    for tid, node in taxonomy.items():
        if not isinstance(node, dict):
            continue
        names = []
        for lang in ("en", "fr", "de", "es", "it"):
            val = node.get(f"name:{lang}") or node.get("name", {}).get(lang) if isinstance(node.get("name"), dict) else None
            if isinstance(val, str):
                names.append(val)
            elif isinstance(val, list):
                names.extend(str(x) for x in val)
        # OFF taxonomy often stores name as {"en": "..."}
        name_obj = node.get("name")
        if isinstance(name_obj, dict):
            for v in name_obj.values():
                if isinstance(v, str):
                    names.append(v)
                elif isinstance(v, list):
                    names.extend(str(x) for x in v)
        syn_obj = node.get("synonyms") or {}
        if isinstance(syn_obj, dict):
            for v in syn_obj.values():
                if isinstance(v, str):
                    names.append(v)
                elif isinstance(v, list):
                    names.extend(str(x) for x in v)
        primary = None
        en = None
        if isinstance(name_obj, dict):
            en = name_obj.get("en")
            if isinstance(en, list) and en:
                en = en[0]
        primary = (en or tid or "").lower().strip()
        if not primary:
            continue
        for n in names:
            key = str(n).lower().strip()
            if key:
                out.setdefault(key, primary)
        out.setdefault(primary, primary)
        out.setdefault(str(tid).lower().removeprefix("en:"), primary)
    return out


def _parents(node: dict) -> list[str]:
    parents = node.get("parents") or node.get("parent") or []
    if isinstance(parents, str):
        parents = [parents]
    return [str(p).lower().removeprefix("en:") for p in parents]


def _has_known_hazard_profile(name: str) -> bool:
    """True if name (or resolve) carries a known allergy/medical hazard flag."""
    if hazard_hits_in_text(name):
        return True
    info = _resolve_atom(name)
    flags = info.get("flags") or {}
    return any(flags.get(f) for f in HAZARD_CLASS_TO_FLAG.values())


def _ancestry_hazard(atom: str, taxonomy: dict) -> str | None:
    key = atom.lower().strip()
    # Find node
    node = None
    if key in taxonomy:
        node = taxonomy[key]
    else:
        for tid, n in taxonomy.items():
            if not isinstance(n, dict):
                continue
            name_obj = n.get("name") or {}
            en = name_obj.get("en") if isinstance(name_obj, dict) else None
            if isinstance(en, list):
                en = en[0] if en else None
            if isinstance(en, str) and en.lower() == key:
                node = n
                break
    if not node:
        return None
    queue = list(_parents(node))
    seen = set()
    while queue:
        p = queue.pop(0)
        if p in seen:
            continue
        seen.add(p)
        if _has_known_hazard_profile(p):
            return p
        n = taxonomy.get(p) or taxonomy.get(f"en:{p}")
        if isinstance(n, dict):
            queue.extend(_parents(n))
    return None


def main() -> int:
    by_code = _cache_by_code()
    held = json.loads(_IDS_PATH.read_text(encoding="utf-8"))
    freq_ids = json.loads(_FREQ_PATH.read_text(encoding="utf-8"))

    if _FREQ_PROGRESS.exists():
        freq = Counter(json.loads(_FREQ_PROGRESS.read_text(encoding="utf-8")).get("freq") or {})
    else:
        held_codes = {p["code"] for p in held.get("products") or []}
        train = [p for p in freq_ids.get("products") or [] if p["code"] not in held_codes]
        # Prefer cache-only scan via accumulate which fetches; use local flatten of cache
        freq = Counter()
        for meta in train:
            prod = by_code.get(meta["code"])
            if not prod:
                continue
            for a in flatten_ingredients(prod.get("ingredients_text") or ""):
                if a:
                    freq[a.lower()] += 1

    promote = {name for name, _ in freq.most_common(_K)}
    taxonomy = load_off_taxonomy()
    syn_map = _taxonomy_synonyms(taxonomy)

    # Collect L5 instances beyond K
    tail_instances: list[str] = []
    for meta in held.get("products") or []:
        prod = by_code.get(meta["code"])
        if not prod:
            continue
        for a in flatten_ingredients(prod.get("ingredients_text") or ""):
            if not a:
                continue
            key = a.lower()
            if key in promote:
                continue
            info = _resolve_atom(a)
            if info["layer_bucket"] != "L5_unknown":
                continue
            tail_instances.append(a)

    n = len(tail_instances)
    a_hit = b_hit = c_hit = 0
    a_ex, b_ex, c_ex = [], [], []
    for a in tail_instances:
        stripped = _strip_modifiers(a)
        if stripped and stripped.lower() != a.lower():
            info = _resolve_atom(stripped)
            if info["layer_bucket"] != "L5_unknown" or stripped.lower() in promote:
                a_hit += 1
                if len(a_ex) < 12:
                    a_ex.append({"from": a, "to": stripped, "layer": info["layer_bucket"]})
        syn = syn_map.get(a.lower())
        if syn and syn != a.lower():
            info = _resolve_atom(syn)
            if info["layer_bucket"] != "L5_unknown" or syn in promote:
                b_hit += 1
                if len(b_ex) < 12:
                    b_ex.append({"from": a, "to": syn, "layer": info["layer_bucket"]})
        anc = _ancestry_hazard(a, taxonomy)
        if anc:
            c_hit += 1
            if len(c_ex) < 12:
                c_ex.append({"from": a, "ancestor": anc})

    def _rate(x):
        return round(x / n, 4) if n else 0.0

    report = {
        "k": _K,
        "n_tail_l5_instances_beyond_k": n,
        "held_products_with_text": sum(
            1 for m in held.get("products") or [] if by_code.get(m["code"])
        ),
        "held_n": len(held.get("products") or []),
        "freq_promote_source": {
            "progress_exists": _FREQ_PROGRESS.exists(),
            "n_distinct": len(freq),
            "dump_date": freq_ids.get("dump_date"),
        },
        "lever_a_modifier_stripping": {
            "n_uplift": a_hit,
            "rate": _rate(a_hit),
            "examples": a_ex,
        },
        "lever_b_off_taxonomy_synonyms": {
            "n_uplift": b_hit,
            "rate": _rate(b_hit),
            "taxonomy_n": len(taxonomy),
            "synonym_map_n": len(syn_map),
            "examples": b_ex,
        },
        "lever_c_off_ancestry_known_hazard": {
            "n_uplift": c_hit,
            "rate": _rate(c_hit),
            "examples": c_ex,
        },
        "note": (
            "Report-only. Uplift = tail L5 instance becomes non-L5 (or in promote set) "
            "after the lever. Levers are measured independently (not stacked)."
        ),
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "note"}, indent=2)[:2000])
    print("path", _OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
