#!/usr/bin/env python3
"""Derive-diff audit: flags lexicon/derive adds that stored rows lack.

Scans distinct atoms from Item 44 dump lists + ontology / e-number catalog
names. Ranks by frequency. Writes JSON report under .local_reports/.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.truth_anchor import all_anchors
from core.normalization.normalizer import normalize_ingredient_key
from core.normalization.parser import flatten_ingredients
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG, hazard_hits_in_text

_DUMP = _BACKEND / ".local_reports" / "item44_dump_ingredients.jsonl"
_ONTOLOGY = _BACKEND.parent / "data" / "ontology.json"
_E_CATALOG = _BACKEND.parent / "data" / "e_number_catalog.json"
_OUT = _BACKEND / ".local_reports" / "item44_derive_diff_audit.json"

_HAZARD_FLAGS = frozenset(HAZARD_CLASS_TO_FLAG.values())

def _lang(name: str) -> str:
    n = name.lower()
    if re.search(r"[äöüß]|milch|mehl|joghurt|hafer", n):
        return "de"
    if re.search(r"lait|beurre|crème|blé|farine|cacahu", n):
        return "fr"
    if re.search(r"leche|mantequilla|queso|almendra", n):
        return "es"
    if re.search(r"latte|burro|formaggio|mandorla", n):
        return "it"
    if re.search(r"\bmelk\b|\bboter\b|\bkaas\b|amandel", n):
        return "nl"
    return "en"


def _classify(name: str, flag: str) -> str:
    """Heuristic: false friend / real gap / ambiguous."""
    hits = hazard_hits_in_text(name)
    # If derive adds dairy but lexicon has no dairy hit after masks → shouldn't happen
    flag_to_cls = {v: k for k, v in HAZARD_CLASS_TO_FLAG.items()}
    cls = flag_to_cls.get(flag)
    if cls and cls not in hits:
        return "false_friend"
    # plant-looking names with animal flags
    if flag in ("dairy_source", "egg_source") and re.search(
        r"\b(vegan|plant[\s\-]*based|tofu|almond|oat|coconut|cocoa|shea|peanut)\b",
        name,
        re.I,
    ):
        return "false_friend"
    if flag in _HAZARD_FLAGS:
        return "real_gap"
    return "ambiguous"


def _atom_freq_from_dump() -> Counter[str]:
    freq: Counter[str] = Counter()
    if not _DUMP.exists():
        return freq
    with _DUMP.open() as fh:
        for line in fh:
            row = json.loads(line)
            raw = (row.get("ingredients_text") or "").strip()
            if not raw:
                continue
            for a in flatten_ingredients(raw):
                n = normalize_ingredient_key(a)
                if n:
                    freq[n] += 1
    return freq


def _stored_flag_sets() -> dict[str, set[str]]:
    """name -> flags that are True on L1 / ontology / e-number rows."""
    out: dict[str, set[str]] = {}
    for key, fact in all_anchors().items():
        flags = {k for k, v in (fact.flags or {}).items() if v is True and k in _HAZARD_FLAGS}
        out.setdefault(normalize_ingredient_key(key), set()).update(flags)
        out.setdefault(normalize_ingredient_key(fact.canonical_name), set()).update(flags)
    if _ONTOLOGY.exists():
        data = json.loads(_ONTOLOGY.read_text())
        rows = data if isinstance(data, list) else data.get("ingredients") or data.get("records") or []
        if isinstance(data, dict) and not rows:
            rows = list(data.values()) if data and isinstance(next(iter(data.values()), None), dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = normalize_ingredient_key(row.get("canonical_name") or row.get("name") or "")
            if not name:
                continue
            flags = {k for k in _HAZARD_FLAGS if row.get(k) is True}
            out.setdefault(name, set()).update(flags)
            for al in row.get("aliases") or []:
                out.setdefault(normalize_ingredient_key(al), set()).update(flags)
    if _E_CATALOG.exists():
        cat = json.loads(_E_CATALOG.read_text())
        entries = cat.get("entries") or cat if isinstance(cat, dict) else cat
        if isinstance(entries, dict):
            entries = entries.values()
        for row in entries or []:
            if not isinstance(row, dict):
                continue
            name = normalize_ingredient_key(row.get("canonical_name") or row.get("name") or "")
            if not name:
                continue
            fl = row.get("flags") or row
            flags = {k for k in _HAZARD_FLAGS if fl.get(k) is True}
            out.setdefault(name, set()).update(flags)
    return out


def main() -> int:
    atom_freq = _atom_freq_from_dump()
    stored = _stored_flag_sets()
    # Universe: dump atoms ∪ stored names
    names = set(atom_freq) | set(stored)
    diffs: list[dict] = []
    for name in names:
        derived = derive_identity_flags(name, {})
        added = []
        have = stored.get(name) or set()
        for flag in _HAZARD_FLAGS:
            if derived.get(flag) and flag not in have:
                added.append(flag)
        if not added:
            continue
        for flag in added:
            diffs.append({
                "name": name,
                "flag": flag,
                "freq": atom_freq.get(name, 0),
                "language": _lang(name),
                "class": _classify(name, flag),
            })
    diffs.sort(key=lambda r: (-r["freq"], r["name"], r["flag"]))
    top200 = diffs[:200]
    by_class = Counter(r["class"] for r in top200)
    # Top-50 derive-only NOT_SAFE radar: names with derive hazard and freq>0
    radar = [r for r in diffs if r["freq"] > 0][:50]
    report = {
        "n_dump_atoms": len(atom_freq),
        "n_stored_names": len(stored),
        "n_universe": len(names),
        "n_diff_rows": len(diffs),
        "top200_by_class": dict(by_class),
        "top200": top200,
        "top50_derive_radar": radar,
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "n_dump_atoms": report["n_dump_atoms"],
        "n_diff_rows": report["n_diff_rows"],
        "top200_by_class": report["top200_by_class"],
        "top10": top200[:10],
        "out": str(_OUT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
