#!/usr/bin/env python3
"""True-only write-back of derive hazard flags onto stored ontology rows.

Replay proof first (default ``--dry-run``): for every ontology name/alias and
e-number catalog name, compute flags ``derive_identity_flags`` adds that the
row lacks. Classify with the **independent** (non-lexicon) heuristic from the
derive-diff audit. Only ``real_gap`` rows are eligible to write.

Does **not** invent rows for dump-only atoms (those stay runtime-derive).
Does **not** write ``false_friend`` / ``ambiguous`` classifications.

Usage::

    python scripts/item44_derive_true_only_writeback.py           # proof JSON
    python scripts/item44_derive_true_only_writeback.py --write  # apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.etl.backfill_asserted_flags import (  # noqa: E402
    backfill_asserted_flags_on_row,
)
from core.knowledge.ike2.flag_derive import derive_identity_flags  # noqa: E402
from core.normalization.normalizer import normalize_ingredient_key  # noqa: E402
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG  # noqa: E402

_HAZARD = frozenset(HAZARD_CLASS_TO_FLAG.values())
_ONTOLOGY = _REPO / "data" / "ontology.json"
_E_CATALOG = _REPO / "data" / "e_number_catalog.json"
_PROOF = _BACKEND / ".local_reports" / "item44_derive_writeback_proof.json"


def _classify(name: str, flag: str) -> str:
    """Independent of hazard_lexicon; prefer false_friend over silent write.

    Only high-confidence name→flag pairs are ``real_gap``. Everything else is
    ``ambiguous`` or ``false_friend`` and is never written.
    """
    n = re.sub(r"_+", "", (name or "").lower())
    # --- hard false friends ---
    if flag == "dairy_source" and re.search(
        r"milk of magnesia|bean curd|soybean curd|milk[\s\-]*like|"
        r"parrotfish|cream parrot|malai seethapalam",
        n,
    ):
        return "false_friend"
    if flag == "tree_nut_source" and re.search(r"brazil wax|water chestnut", n):
        return "false_friend"
    if flag == "gluten_source" and re.search(
        r"\b(idli|rice|rava|ravai)\b.*\b(semolina|suji|sooji|rava)\b|"
        r"\brice semolina\b|\bidli semolina\b|\bkalle puri\b",
        n,
    ):
        return "false_friend"
    # --- high-confidence real gaps only ---
    if flag == "dairy_source":
        if re.search(
            r"\b(buttermilk|whey|casein|caseinate|lactose|paneer|ghee|"
            r"yoghurt|yogurt)\b|"
            r"\b(flavoured|flavored|cultured)\s+milks?\b|"
            r"\btraditional buttermilk\b",
            n,
        ):
            return "real_gap"
        return "ambiguous"
    if flag == "egg_source":
        if re.search(r"\begg lecithin\b|\begg yolk\b|\begg white\b|\beggs?\b", n) and (
            "eggplant" not in n and "vegan" not in n
        ):
            return "real_gap"
        return "ambiguous"
    if flag == "fish_source":
        if re.search(r"\bfish collagen\b|\bfish gelatin\b|\bfish sauce\b", n):
            return "real_gap"
        # umbrella alias text on shellfish rows — leave to curation
        return "ambiguous"
    if flag == "gluten_source":
        if re.search(r"\b(maize|corn|wheat|sorghum)\s+gluten(\s+feed)?\b", n):
            return "real_gap"
        return "ambiguous"
    if flag == "soy_source":
        if re.fullmatch(r"soy|soya|soybean|soybeans", n):
            return "real_gap"
        return "ambiguous"
    return "ambiguous"


def _stored_trues(row: dict) -> set[str]:
    nested = row.get("flags") if isinstance(row.get("flags"), dict) else {}
    return {k for k in _HAZARD if row.get(k) is True or nested.get(k) is True}


def _gaps_for_name(name: str, row: dict) -> list[str]:
    stored = _stored_trues(row)
    derived = derive_identity_flags(name, dict(row))
    return [f for f in _HAZARD if derived.get(f) is True and f not in stored]


def _apply_trues(row: dict, flags: list[str]) -> dict:
    out = dict(row)
    for f in flags:
        out[f] = True
        if f in ("dairy_source", "egg_source", "fish_source", "shellfish_source"):
            out["animal_origin"] = True
    return backfill_asserted_flags_on_row(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--write",
        action="store_true",
        help="apply real_gap trues to ontology.json (default is dry-run proof only)",
    )
    ap.add_argument("--ontology", type=Path, default=_ONTOLOGY)
    args = ap.parse_args()

    data = json.loads(args.ontology.read_text(encoding="utf-8"))
    ingredients = list(data.get("ingredients") or [])
    # canonical_name → index (first wins); also map aliases → index
    index_by_key: dict[str, int] = {}
    for i, row in enumerate(ingredients):
        canon = normalize_ingredient_key(row.get("canonical_name") or "")
        if canon and canon not in index_by_key:
            index_by_key[canon] = i
        for al in row.get("aliases") or []:
            an = normalize_ingredient_key(al)
            if an and an not in index_by_key:
                index_by_key[an] = i

    proof_rows = []
    # Collect per-row flag unions (keyed by ingredient index).
    # Only the canonical_name surface may write — never an alias (alias
    # "egg lecithin" must not mark the whole "lecithin" group as egg).
    to_apply: dict[int, set[str]] = {}
    for key, idx in index_by_key.items():
        row = ingredients[idx]
        canon = normalize_ingredient_key(row.get("canonical_name") or "")
        for flag in _gaps_for_name(key, row):
            cls = _classify(key, flag)
            proof_rows.append(
                {
                    "name": key,
                    "canonical_name": row.get("canonical_name"),
                    "flag": flag,
                    "class": cls,
                    "writable": bool(cls == "real_gap" and key == canon),
                }
            )
            if cls == "real_gap" and key == canon:
                to_apply.setdefault(idx, set()).add(flag)

    by_class = Counter(r["class"] for r in proof_rows)
    proof = {
        "n_ontology_rows": len(ingredients),
        "n_name_keys": len(index_by_key),
        "n_gap_rows": len(proof_rows),
        "by_class": dict(by_class),
        "n_rows_to_write": len(to_apply),
        "n_flags_to_write": sum(len(v) for v in to_apply.values()),
        "gaps": sorted(proof_rows, key=lambda r: (r["class"], r["name"], r["flag"])),
        "write": bool(args.write),
    }
    _PROOF.parent.mkdir(parents=True, exist_ok=True)
    _PROOF.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: proof[k] for k in proof if k != "gaps"},
            indent=2,
        )
    )
    print("proof", _PROOF)

    if not args.write:
        return 0

    changed = 0
    for idx, flags in sorted(to_apply.items()):
        before = ingredients[idx]
        after = _apply_trues(before, sorted(flags))
        if after != before:
            ingredients[idx] = after
            changed += 1
    data["ingredients"] = ingredients
    args.ontology.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote ontology rows_changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
