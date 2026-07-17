#!/usr/bin/env python3
"""Auto-fix common ontology.json structural errors before validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_BACKEND = _REPO / "backend"
sys.path.insert(0, str(_BACKEND))

from core.config import get_ontology_path

_BOOLEAN_FLAGS = (
    "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "root_vegetable", "onion_source", "garlic_source", "fermented",
)
_LIST_FIELDS = ("aliases", "derived_from", "contains", "may_contain", "uncertainty_flags", "regions")
_VALID_KNOWLEDGE_STATES = frozenset({"UNKNOWN", "DISCOVERED", "AUTO_CLASSIFIED", "VERIFIED", "LOCKED"})


def fix_entry(entry: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    entry_id = entry.get("id", "?")

    if not entry.get("id"):
        return changes

    if not entry.get("canonical_name"):
        entry["canonical_name"] = entry["id"].replace("_", " ")
        changes.append(f"{entry_id}: set canonical_name from id")

    state = entry.get("knowledge_state")
    if state not in _VALID_KNOWLEDGE_STATES:
        entry["knowledge_state"] = "UNKNOWN"
        changes.append(f"{entry_id}: knowledge_state {state!r} -> UNKNOWN")

    for flag in _BOOLEAN_FLAGS:
        val = entry.get(flag)
        if val is None:
            entry[flag] = False
            changes.append(f"{entry_id}: {flag} null -> false")
        elif not isinstance(val, bool):
            entry[flag] = bool(val)
            changes.append(f"{entry_id}: {flag} coerced to bool")

    for field in _LIST_FIELDS:
        if entry.get(field) is None:
            entry[field] = []
            changes.append(f"{entry_id}: {field} null -> []")
        elif not isinstance(entry.get(field), list):
            entry[field] = [entry[field]]
            changes.append(f"{entry_id}: {field} wrapped in list")

    if entry.get("aliases") is not None:
        deduped = []
        seen = set()
        for alias in entry["aliases"]:
            if not isinstance(alias, str):
                continue
            key = alias.strip().lower()
            if key and key not in seen:
                deduped.append(alias)
                seen.add(key)
        if deduped != entry["aliases"]:
            entry["aliases"] = deduped
            changes.append(f"{entry_id}: deduped aliases")

    return changes


def main() -> int:
    path = get_ontology_path()
    backup = path.with_suffix(".json.bak")
    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients") or []

    all_changes: list[str] = []
    for entry in ingredients:
        all_changes.extend(fix_entry(entry))

    if not all_changes:
        print("No fixes needed.")
        return 0

    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Applied {len(all_changes)} fixes (backup: {backup})")
    for change in all_changes[:30]:
        print(f"  - {change}")
    if len(all_changes) > 30:
        print(f"  ... and {len(all_changes) - 30} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
