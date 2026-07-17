#!/usr/bin/env python3
"""Resolve cross-entry alias/canonical name conflicts in ontology.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_BACKEND = _REPO / "backend"
sys.path.insert(0, str(_BACKEND))

from core.config import get_ontology_path

_STATE_PRIORITY = {"LOCKED": 5, "VERIFIED": 4, "AUTO_CLASSIFIED": 3, "DISCOVERED": 2, "UNKNOWN": 1}
# Curated winners for known cross-entry conflicts (normalized key -> entry id)
_RESOLUTION_OVERRIDES = {
    "cochineal": "carmine",
    "sodium bicarbonate": "sodium_bicarbonate",
    "modified starch": "modified_starch",
    "sunflower lecithin": "sunflower_lecithin",
}


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _entry_score(entry: dict[str, Any], key_norm: str) -> tuple[int, int, int, int, str]:
    state = _STATE_PRIORITY.get(entry.get("knowledge_state") or "UNKNOWN", 0)
    quality = sum(
        1 for flag in (
            entry.get("animal_origin"),
            entry.get("plant_origin"),
            entry.get("insect_derived"),
            entry.get("synthetic"),
            entry.get("fungal"),
            entry.get("dairy_source"),
            entry.get("egg_source"),
        ) if flag
    )
    canonical_match = 1 if _norm(entry.get("canonical_name", "")) == key_norm else 0
    alias_count = len(entry.get("aliases") or [])
    return (state, quality, canonical_match, alias_count, entry.get("id", ""))


def _merge_into(winner: dict[str, Any], loser: dict[str, Any]) -> None:
    merged_aliases = list(winner.get("aliases") or [])
    seen = {_norm(a) for a in merged_aliases}
    for alias in (loser.get("aliases") or []) + [loser.get("canonical_name", "")]:
        if alias and _norm(alias) not in seen:
            merged_aliases.append(alias)
            seen.add(_norm(alias))
    winner["aliases"] = merged_aliases

    for flag in (
        "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
        "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    ):
        if loser.get(flag):
            winner[flag] = True


def resolve_conflicts(ingredients: list[dict[str, Any]]) -> list[str]:
    changes: list[str] = []
    by_id = {e["id"]: e for e in ingredients if e.get("id")}

    index: dict[str, list[str]] = {}
    for entry in ingredients:
        eid = entry.get("id")
        if not eid:
            continue
        keys = list(entry.get("aliases") or []) + [entry.get("canonical_name", "")]
        for key in keys:
            nk = _norm(key)
            if nk:
                index.setdefault(nk, []).append(eid)

    conflicts = {k: sorted(set(v)) for k, v in index.items() if len(set(v)) > 1}

    for key_norm, entry_ids in sorted(conflicts.items()):
        canonical_owners = [
            eid for eid in entry_ids
            if _norm(by_id[eid].get("canonical_name", "")) == key_norm
        ]

        if key_norm in _RESOLUTION_OVERRIDES and _RESOLUTION_OVERRIDES[key_norm] in entry_ids:
            winner_id = _RESOLUTION_OVERRIDES[key_norm]
            winner = by_id[winner_id]
            ranked = sorted(entry_ids, key=lambda eid: _entry_score(by_id[eid], key_norm), reverse=True)
        elif len(canonical_owners) == 1:
            winner_id = canonical_owners[0]
            winner = by_id[winner_id]
            ranked = sorted(entry_ids, key=lambda eid: _entry_score(by_id[eid], key_norm), reverse=True)
        else:
            ranked = sorted(entry_ids, key=lambda eid: _entry_score(by_id[eid], key_norm), reverse=True)
            winner_id = ranked[0]
            winner = by_id[winner_id]

        if len(canonical_owners) > 1:
            ranked_owners = sorted(
                canonical_owners,
                key=lambda eid: _entry_score(by_id[eid], key_norm),
                reverse=True,
            )
            keep_id = ranked_owners[0]
            keep = by_id[keep_id]
            for drop_id in ranked_owners[1:]:
                drop = by_id[drop_id]
                _merge_into(keep, drop)
                changes.append(
                    f"Merged duplicate canonical {key_norm!r}: keep {keep_id}, removed {drop_id}"
                )
                ingredients[:] = [e for e in ingredients if e.get("id") != drop_id]
                by_id.pop(drop_id, None)
            winner_id = keep_id
            winner = keep
            ranked = [eid for eid in ranked if eid in by_id]

        for loser_id in ranked:
            if loser_id == winner_id:
                continue
            loser = by_id.get(loser_id)
            if not loser:
                continue

            if _norm(loser.get("canonical_name", "")) == key_norm:
                _merge_into(winner, loser)
                changes.append(
                    f"Merged canonical {key_norm!r}: keep {winner_id}, removed entry {loser_id}"
                )
                ingredients[:] = [e for e in ingredients if e.get("id") != loser_id]
                by_id.pop(loser_id, None)
                continue

            original_aliases = list(loser.get("aliases") or [])
            new_aliases = [a for a in original_aliases if _norm(a) != key_norm]
            if new_aliases != original_aliases:
                loser["aliases"] = new_aliases
                removed = [a for a in original_aliases if _norm(a) == key_norm]
                changes.append(
                    f"Removed alias {removed!r} from {loser_id} (kept on {winner_id})"
                )

    return changes


def main() -> int:
    path = get_ontology_path()
    backup = path.with_suffix(".json.bak")
    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients") or []

    changes = resolve_conflicts(ingredients)

    if not changes:
        print("No duplicate alias conflicts found.")
        return 0

    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    data["ingredients"] = ingredients
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Resolved {len(changes)} conflict(s) (backup: {backup})")
    for change in changes:
        print(f"  - {change}")
    print(f"Entries after resolution: {len(ingredients)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
