#!/usr/bin/env python3
"""Item 56: export a 300-row random derive-hit sample for hand labeling.

Each row is one (atom, flag) where ``derive_identity_flags`` fired True.
Labels stay empty in the committed golden CSV — the owner fills ``label``
with tp/fp (see docs/item56_derive_hit_labeling.md).

Usage (from backend/):
    python scripts/export_derive_hit_sample.py
    python scripts/export_derive_hit_sample.py --out /tmp/hits.csv --n 300 --seed 56
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.normalization.normalizer import normalize_ingredient_key
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG

_REPO = _BACKEND.parent
_ONTOLOGY = _REPO / "data" / "ontology.json"
_E_CATALOG = _REPO / "data" / "e_number_catalog.json"
GOLDEN_PATH = _BACKEND / "tests" / "ike2" / "golden" / "derive_hit_labels.csv"

SAMPLE_SIZE = 300
DEFAULT_SEED = 56
COLUMNS = ("atom", "flag", "context", "language", "label")
_HAZARD_FLAGS = tuple(HAZARD_CLASS_TO_FLAG.values())


def infer_language(name: str) -> str:
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


def _iter_named_rows() -> list[tuple[str, str, str]]:
    """Yield (atom, context, language_hint_source) from static stores."""
    out: list[tuple[str, str, str]] = []
    if _ONTOLOGY.exists():
        data = json.loads(_ONTOLOGY.read_text(encoding="utf-8"))
        rows = data.get("ingredients") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = (row.get("canonical_name") or "").strip()
            if name:
                out.append((name, "ontology", name))
            for alias in row.get("aliases") or []:
                alias = (alias or "").strip()
                if alias:
                    out.append((alias, f"ontology_alias:{name}", alias))
    if _E_CATALOG.exists():
        raw = json.loads(_E_CATALOG.read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else raw.get("entries") or []
        for row in entries:
            if not isinstance(row, dict):
                continue
            name = (row.get("canonical_name") or row.get("name") or "").strip()
            if name:
                out.append((name, "e_number_catalog", name))
    return out


def collect_derive_hits() -> list[dict[str, str]]:
    """All (atom, flag) pairs where identity derive fired a hazard true."""
    seen: set[tuple[str, str]] = set()
    hits: list[dict[str, str]] = []
    for atom, context, lang_src in _iter_named_rows():
        if len(atom) > 80 or atom.count(",") >= 2:
            continue
        derived = derive_identity_flags(atom, {})
        for flag in _HAZARD_FLAGS:
            if derived.get(flag) is not True:
                continue
            key = (normalize_ingredient_key(atom), flag)
            if key in seen:
                continue
            seen.add(key)
            hits.append({
                "atom": atom,
                "flag": flag,
                "context": context,
                "language": infer_language(lang_src),
                "label": "",
            })
    return hits


def sample_hits(
    hits: list[dict[str, str]],
    *,
    n: int = SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, str]]:
    if len(hits) < n:
        raise ValueError(f"need at least {n} derive hits, got {len(hits)}")
    rng = random.Random(seed)
    picked = rng.sample(hits, n)
    picked.sort(key=lambda r: (r["flag"], r["atom"], r["context"]))
    return picked


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in COLUMNS})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=GOLDEN_PATH)
    p.add_argument("--n", type=int, default=SAMPLE_SIZE)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args(argv)
    hits = collect_derive_hits()
    sample = sample_hits(hits, n=args.n, seed=args.seed)
    write_csv(args.out, sample)
    print(f"wrote {len(sample)} unlabeled derive hits to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
