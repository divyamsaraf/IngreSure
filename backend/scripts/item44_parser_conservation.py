#!/usr/bin/env python3
"""Parser conservation audit: raw hazard lexicon vs parsed atoms.

Scans held-out (216) + frequency (9000) OFF lists using the local product
cache when present. Writes ``backend/.local_reports/item44_conservation.json``.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from core.normalization.parser import flatten_ingredients
from core.parsing.hazard_lexicon import conservation_misses, hazard_hits_in_text

_HELD = _REPO / "data" / "item44_off_product_ids.json"
_FREQ = _REPO / "data" / "item44_off_freq_product_ids.json"
_CACHE = _BACKEND / ".local_reports" / "item44_off_product_cache.json"
_OUT = _BACKEND / ".local_reports" / "item44_conservation.json"

_PATTERN_CLASSIFIERS = (
    ("percent_paren", re.compile(r"\([^)]*\d+[.,]?\d*\s*%[^)]*\)")),
    ("percent_trailing", re.compile(r"\b\w[\w\s]*\d+[.,]?\d*\s*%")),
    ("brackets", re.compile(r"\[[^\]]+\]")),
    ("colons", re.compile(r":")),
    ("and_or", re.compile(r"\band/or\b", re.I)),
    ("semicolons", re.compile(r";")),
    ("line_breaks", re.compile(r"[\r\n]")),
    ("ocr_noise", re.compile(r"[|_~]{2,}|\b[lI]0dise|\blodised\b|\blodized\b", re.I)),
    ("parentheticals", re.compile(r"\([^)]+\)")),
)


def _classify_raw(raw: str) -> list[str]:
    tags = []
    for name, pat in _PATTERN_CLASSIFIERS:
        if pat.search(raw or ""):
            tags.append(name)
    return tags or ["unclassified"]


def _load_cache() -> dict[str, dict]:
    if not _CACHE.exists():
        return {}
    raw = json.loads(_CACHE.read_text(encoding="utf-8"))
    by_code: dict[str, dict] = {}
    for k, v in raw.items():
        if not v or not isinstance(v, dict):
            continue
        code = str(v.get("code") or k.split("|", 1)[0]).strip()
        text = (v.get("ingredients_text") or "").strip()
        if code and text and code not in by_code:
            by_code[code] = v
    return by_code


def _scan(products: list[dict], cache: dict[str, dict], label: str) -> dict:
    misses = []
    scanned = 0
    missing_text = 0
    pattern_counts: Counter = Counter()
    hazard_miss_counts: Counter = Counter()
    for meta in products:
        code = meta["code"]
        prod = cache.get(code)
        if not prod:
            missing_text += 1
            continue
        raw = (prod.get("ingredients_text") or "").strip()
        if not raw:
            missing_text += 1
            continue
        scanned += 1
        atoms = [a for a in flatten_ingredients(raw) if a]
        lost = conservation_misses(raw, atoms)
        if not lost:
            continue
        patterns = _classify_raw(raw)
        for p in patterns:
            pattern_counts[p] += 1
        for h in lost:
            hazard_miss_counts[h] += 1
        misses.append(
            {
                "code": code,
                "market": meta.get("market"),
                "corpus": label,
                "lost_hazards": sorted(lost),
                "raw_hazards": sorted(hazard_hits_in_text(raw)),
                "atom_hazards": sorted(hazard_hits_in_text(" ".join(atoms))),
                "patterns": patterns,
                "atoms": atoms[:40],
                "raw_excerpt": raw[:240],
            }
        )
    by_pattern: dict[str, list] = defaultdict(list)
    for m in misses:
        for p in m["patterns"]:
            if len(by_pattern[p]) < 15:
                by_pattern[p].append(
                    {
                        "code": m["code"],
                        "lost_hazards": m["lost_hazards"],
                        "raw_excerpt": m["raw_excerpt"],
                        "atoms": m["atoms"][:12],
                    }
                )
    return {
        "label": label,
        "n_products": len(products),
        "scanned": scanned,
        "missing_text": missing_text,
        "n_miss_lists": len(misses),
        "pattern_counts": dict(pattern_counts),
        "hazard_miss_counts": dict(hazard_miss_counts),
        "examples_by_pattern": dict(by_pattern),
        "misses": misses,
    }


def main() -> int:
    cache = _load_cache()
    held = json.loads(_HELD.read_text(encoding="utf-8")).get("products") or []
    freq = json.loads(_FREQ.read_text(encoding="utf-8")).get("products") or []
    print(f"cache codes={len(cache)} held={len(held)} freq={len(freq)}", flush=True)
    held_r = _scan(held, cache, "held_out_216")
    freq_r = _scan(freq, cache, "freq_9000")
    report = {
        "parser": "flatten_ingredients (post composition-percent fix)",
        "held_out": {k: v for k, v in held_r.items() if k != "misses"},
        "freq": {k: v for k, v in freq_r.items() if k != "misses"},
        "held_out_misses": held_r["misses"],
        "freq_misses_sample": freq_r["misses"][:200],
        "n_freq_misses": freq_r["n_miss_lists"],
        "raw_string_hazard_sweep": {
            "status": "implemented",
            "rule": (
                "After flatten+resolve+evaluate, scan the raw ingredient string with "
                "HAZARD_LEXICON. Each hit stands as a product-level Avoid for matching "
                "medical restrictions (OR with atom-derived Avoids), attributed to "
                "'label text'. Parser failure can only add hazards, never remove them. "
                "Negation / false-friend filters apply. Parse-quality ceiling "
                "(truncation, unbalanced parentheses, OCR noise, unparsed Contains "
                "footnote) caps firm SAFE at UNCERTAIN."
            ),
            "seam": "compliance.evaluate(..., raw_label=)",
        },
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "held_scanned": held_r["scanned"],
                "held_misses": held_r["n_miss_lists"],
                "held_patterns": held_r["pattern_counts"],
                "freq_scanned": freq_r["scanned"],
                "freq_misses": freq_r["n_miss_lists"],
                "freq_patterns": freq_r["pattern_counts"],
                "path": str(_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
