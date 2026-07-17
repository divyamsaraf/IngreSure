#!/usr/bin/env python3
"""
Merge all staging sources into data/ontology.json.

Uses the same merge semantics as scripts/merge_e_numbers_to_ontology.py:
- OR boolean flags into existing entries
- Add new aliases without duplicates
- Never downgrade VERIFIED / LOCKED entries

Run from repo root:
  python backend/scripts/merge_all_sources.py
  python backend/scripts/merge_all_sources.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_ONTOLOGY_PATH = _REPO / "data" / "ontology.json"
_BACKUP_PATH = _REPO / "data" / "ontology.json.bak"
_E_NUMBER_CATALOG = _REPO / "data" / "e_number_catalog.json"
_INDIA_CATALOG_PATHS = (
    _REPO / "backend" / "data" / "india_ingredients_catalog.json",
    _REPO / "data" / "india_ingredients_catalog.json",
)
_STAGING_SOURCES = (
    ("open_food_facts", _REPO / "data" / "off_staging.json"),
    ("usda_fdc", _REPO / "data" / "usda_staging.json"),
    ("wikidata", _REPO / "data" / "wikidata_staging.json"),
)
_REPORT_PATH = _REPO / "data" / "merge_report.json"

_VALID_KNOWLEDGE_STATES = frozenset({
    "UNKNOWN", "DISCOVERED", "AUTO_CLASSIFIED", "VERIFIED", "LOCKED",
})
_PROTECTED_STATES = frozenset({"VERIFIED", "LOCKED"})

_BOOLEAN_FLAGS = (
    "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "root_vegetable", "onion_source", "garlic_source", "fermented",
)
_OPTIONAL_FIELDS = ("animal_species", "nut_source", "alcohol_content")
_LIST_FIELDS = ("uncertainty_flags", "regions", "derived_from", "contains", "may_contain")

DEFAULT_ENTRY: dict[str, Any] = {
    "derived_from": [],
    "contains": [],
    "may_contain": [],
    "animal_origin": False,
    "plant_origin": False,
    "synthetic": False,
    "fungal": False,
    "insect_derived": False,
    "animal_species": None,
    "egg_source": False,
    "dairy_source": False,
    "gluten_source": False,
    "nut_source": None,
    "soy_source": False,
    "sesame_source": False,
    "alcohol_content": None,
    "root_vegetable": False,
    "onion_source": False,
    "garlic_source": False,
    "fermented": False,
    "uncertainty_flags": [],
    "regions": [],
    "knowledge_state": "UNKNOWN",
}

_CATEGORY_RE = re.compile(
    r"\b(products?|categories|category|meals?|entrees|side dishes|beverages)\b",
    re.I,
)
_METADATA_KEYS = frozenset({
    "_source", "_off_id", "_wikidata", "_fdc_id", "_usda_category",
    "_cas_number", "_inchi", "_e_number",
})


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _norm_key(s: str) -> str:
    return _norm_name(s).replace(" ", "_")


def _slug(name: str) -> str:
    s = _norm_key(name)
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return s.strip("_") or "unknown"


def _e_id(e_code: str) -> str:
    return _norm_name(e_code).replace(" ", "")


def _is_protected(entry: dict[str, Any]) -> bool:
    return (entry.get("knowledge_state") or "UNKNOWN") in _PROTECTED_STATES


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _is_plausible_ingredient(entry: dict[str, Any]) -> bool:
    canonical = _norm_name(entry.get("canonical_name") or "")
    if len(canonical) < 3:
        return False
    if _CATEGORY_RE.search(canonical):
        return False
    flags = entry.get("uncertainty_flags") or []
    if "product_category_not_single_ingredient" in flags:
        return False
    return True


def _ingredient_keys(entry: dict[str, Any]) -> set[str]:
    keys = {_norm_key(entry.get("id") or ""), _norm_key(entry.get("canonical_name") or "")}
    keys.discard("")
    for alias in entry.get("aliases") or []:
        k = _norm_key(alias)
        if k:
            keys.add(k)
    return keys


class OntologyIndex:
    def __init__(self, ingredients: list[dict[str, Any]]) -> None:
        self.ingredients = ingredients
        self.by_id: dict[str, dict[str, Any]] = {}
        self.key_to_entry: dict[str, dict[str, Any]] = {}
        self.rebuild()

    def rebuild(self) -> None:
        self.by_id = {ing["id"]: ing for ing in self.ingredients if ing.get("id")}
        self.key_to_entry = {}
        for ing in self.ingredients:
            for key in _ingredient_keys(ing):
                self.key_to_entry.setdefault(key, ing)

    def find(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        probes = [_norm_key(entry.get("canonical_name") or "")]
        probes.extend(_norm_key(a) for a in entry.get("aliases") or [])
        if entry.get("id"):
            probes.append(_norm_key(entry["id"]))
        for key in probes:
            if key and key in self.key_to_entry:
                return self.key_to_entry[key]
        return None

    def register(self, entry: dict[str, Any]) -> None:
        if entry.get("id"):
            self.by_id[entry["id"]] = entry
        self.update_keys(entry)

    def update_keys(self, entry: dict[str, Any]) -> None:
        for key in _ingredient_keys(entry):
            self.key_to_entry[key] = entry


def _merge_flags(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for flag in _BOOLEAN_FLAGS:
        if incoming.get(flag):
            existing[flag] = True
    for field in _OPTIONAL_FIELDS:
        if incoming.get(field) is not None:
            existing[field] = incoming[field]
    for field in _LIST_FIELDS:
        merged = list(existing.get(field) or [])
        for item in incoming.get(field) or []:
            if item not in merged:
                merged.append(item)
        existing[field] = merged


def _add_aliases(
    existing: dict[str, Any],
    aliases: list[str],
    *,
    index: OntologyIndex | None = None,
) -> int:
    current = list(existing.get("aliases") or [])
    seen = {_norm_name(a) for a in current}
    seen.add(_norm_name(existing.get("canonical_name") or ""))
    seen.add(_norm_name(existing.get("id") or ""))
    added = 0
    for alias in aliases:
        if not alias:
            continue
        norm = _norm_name(alias)
        if norm in seen:
            continue
        if index is not None:
            owner = index.key_to_entry.get(_norm_key(alias))
            if owner is not None and owner is not existing:
                continue
        current.append(alias)
        seen.add(norm)
        added += 1
    existing["aliases"] = current
    return added


def _copy_default(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    return value


def _shallow_copy_entry(entry: dict[str, Any]) -> dict[str, Any]:
    copied = dict(entry)
    for field in _LIST_FIELDS:
        if field in copied:
            copied[field] = list(copied[field] or [])
    return copied


def _strip_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in raw.items() if k not in _METADATA_KEYS}


def _normalize_entry(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    canonical = _norm_name(raw.get("canonical_name") or raw.get("id") or "")
    entry_id = raw.get("id") or _slug(canonical)
    aliases = list(raw.get("aliases") or [])
    payload = _strip_metadata(raw)
    entry = {
        "id": entry_id,
        "canonical_name": canonical,
        "aliases": [],
        **DEFAULT_ENTRY,
        **{k: v for k, v in payload.items() if k not in ("id", "canonical_name", "aliases")},
    }
    entry["canonical_name"] = canonical
    entry["knowledge_state"] = raw.get("knowledge_state") or "DISCOVERED"
    entry["_source"] = source
    _add_aliases(entry, aliases)
    return entry


def _merge_into_existing(
    target: dict[str, Any],
    incoming: dict[str, Any],
    index: OntologyIndex,
    stats: dict[str, Any],
) -> None:
    if _is_protected(target):
        stats["skipped_protected"] += 1
        return

    aliases = list(incoming.get("aliases") or [])
    aliases.append(incoming.get("canonical_name") or "")
    added = _add_aliases(target, aliases, index=index)
    stats["aliases_added"] += added
    _merge_flags(target, incoming)
    stats["merged_into_existing"] += 1
    index.update_keys(target)


def _create_entry(
    incoming: dict[str, Any],
    index: OntologyIndex,
    stats: dict[str, Any],
) -> bool:
    if not _is_plausible_ingredient(incoming):
        stats["skipped_not_plausible"] += 1
        return False

    entry_id = incoming["id"]
    if entry_id in index.by_id:
        _merge_into_existing(index.by_id[entry_id], incoming, index, stats)
        stats["skipped_duplicates"] += 1
        return False

    new_entry = _shallow_copy_entry(incoming)
    new_entry["knowledge_state"] = "DISCOVERED"
    index.ingredients.append(new_entry)
    index.register(new_entry)
    stats["new_entries"] += 1
    return True


def _merge_generic_source(
    index: OntologyIndex,
    items: list[dict[str, Any]],
    source: str,
    stats: dict[str, Any],
) -> None:
    for raw in items:
        if not isinstance(raw, dict):
            continue
        incoming = _normalize_entry(raw, source=source)
        target = index.find(incoming)
        if target is not None:
            _merge_into_existing(target, incoming, index, stats)
        else:
            _create_entry(incoming, index, stats)


def _merge_e_number_catalog(
    index: OntologyIndex,
    catalog: dict[str, Any],
    stats: dict[str, Any],
) -> None:
    for raw in catalog.get("entries") or []:
        if not isinstance(raw, dict):
            continue

        e_code = raw.get("e_code") or ""
        merge_into = raw.get("merge_into")
        aliases = list(raw.get("aliases") or [])
        if e_code and e_code not in aliases:
            aliases.insert(0, e_code)

        target: dict[str, Any] | None = None
        if merge_into and merge_into in index.by_id:
            target = index.by_id[merge_into]
        else:
            probe_keys = [_e_id(e_code), _norm_key(raw.get("canonical_name", ""))]
            probe_keys.extend(_norm_key(a) for a in aliases[:5])
            for key in probe_keys:
                if key and key in index.key_to_entry:
                    target = index.key_to_entry[key]
                    break

        incoming = _normalize_entry(
            {
                **DEFAULT_ENTRY,
                **{k: v for k, v in raw.items() if k not in ("e_code", "merge_into")},
                "id": _e_id(e_code) if e_code else _slug(raw.get("canonical_name", "")),
                "aliases": aliases,
            },
            source="e_number_catalog",
        )

        if target is not None:
            _merge_into_existing(target, incoming, index, stats)
            continue

        if not _is_plausible_ingredient(incoming):
            stats["skipped_not_plausible"] += 1
            continue

        entry_id = incoming["id"]
        if entry_id in index.by_id:
            _merge_into_existing(index.by_id[entry_id], incoming, index, stats)
            stats["skipped_duplicates"] += 1
            continue

        index.ingredients.append(incoming)
        index.register(incoming)
        stats["new_entries"] += 1


def _merge_entries_into(primary: dict[str, Any], secondary: dict[str, Any]) -> None:
    if _is_protected(primary):
        return
    aliases = list(secondary.get("aliases") or [])
    aliases.append(secondary.get("canonical_name") or "")
    _add_aliases(primary, aliases, index=None)
    _merge_flags(primary, secondary)


def _deduplicate(
    ingredients: list[dict[str, Any]],
    stats: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []

    by_canonical: dict[str, list[dict[str, Any]]] = {}
    for ing in ingredients:
        key = _norm_key(ing.get("canonical_name") or "")
        if key:
            by_canonical.setdefault(key, []).append(ing)

    to_remove: set[int] = set()
    for key, group in by_canonical.items():
        if len(group) < 2:
            continue
        primary = next((g for g in group if _is_protected(g)), group[0])
        for other in group:
            if other is primary:
                continue
            if id(other) in to_remove:
                continue
            _merge_entries_into(primary, other)
            to_remove.add(id(other))
            stats["deduped_same_canonical"] += 1

    remaining = [ing for ing in ingredients if id(ing) not in to_remove]

    alias_to_entry: dict[str, dict[str, Any]] = {}
    for ing in remaining:
        for alias in ing.get("aliases") or []:
            alias_to_entry[_norm_key(alias)] = ing

    to_remove = set()
    for ing in remaining:
        if id(ing) in to_remove:
            continue
        canon_key = _norm_key(ing.get("canonical_name") or "")
        other = alias_to_entry.get(canon_key)
        if other is None or other is ing or id(other) in to_remove:
            continue
        if _is_protected(other) and not _is_protected(ing):
            primary, secondary = other, ing
        else:
            primary, secondary = ing, other
        _merge_entries_into(primary, secondary)
        to_remove.add(id(secondary))
        stats["deduped_alias_canonical"] += 1

    remaining = [ing for ing in remaining if id(ing) not in to_remove]
    ingredients[:] = remaining
    warnings.extend(_near_duplicate_warnings(remaining))
    return warnings


def _near_duplicate_warnings(ingredients: list[dict[str, Any]]) -> list[str]:
    """Flag canonical names with edit distance < 2 (bucketed for performance)."""
    warnings: list[str] = []
    by_bucket: dict[tuple[int, str], list[str]] = {}
    seen_names: set[str] = set()
    for ing in ingredients:
        cn = _norm_name(ing.get("canonical_name") or "")
        if cn and cn not in seen_names:
            seen_names.add(cn)
            prefix = cn[:3] if len(cn) >= 3 else cn
            by_bucket.setdefault((len(cn), prefix), []).append(cn)

    seen_pairs: set[tuple[str, str]] = set()
    for names in by_bucket.values():
        if len(names) < 2:
            continue
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pair = (a, b)
                if pair in seen_pairs:
                    continue
                if _edit_distance(a, b) < 2:
                    seen_pairs.add(pair)
                    warnings.append(
                        f"Near-duplicate canonical names (distance < 2): {a!r} vs {b!r}"
                    )
    return warnings


def _ensure_defaults(entry: dict[str, Any]) -> None:
    for key, value in DEFAULT_ENTRY.items():
        if key not in entry:
            entry[key] = _copy_default(value)
    if entry.get("knowledge_state") not in _VALID_KNOWLEDGE_STATES:
        entry["knowledge_state"] = "UNKNOWN"
    for flag in _BOOLEAN_FLAGS:
        val = entry.get(flag)
        if val is None:
            entry[flag] = False
        elif not isinstance(val, bool):
            entry[flag] = bool(val)


def _validate(ingredients: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_canonical: dict[str, str] = {}
    alias_owner: dict[str, str] = {}

    for ing in ingredients:
        _ensure_defaults(ing)
        entry_id = ing.get("id") or ""
        canonical = _norm_name(ing.get("canonical_name") or "")

        if not entry_id:
            errors.append("Entry missing id")
            continue
        if entry_id in seen_ids:
            errors.append(f"Duplicate id {entry_id!r} ({seen_ids[entry_id]} and {canonical})")
        else:
            seen_ids[entry_id] = canonical

        if not canonical:
            errors.append(f"Entry {entry_id!r} missing canonical_name")
        elif canonical in seen_canonical:
            errors.append(
                f"Duplicate canonical_name {canonical!r} "
                f"({seen_canonical[canonical]} and {entry_id})"
            )
        else:
            seen_canonical[canonical] = entry_id

        state = ing.get("knowledge_state")
        if state not in _VALID_KNOWLEDGE_STATES:
            errors.append(f"Entry {entry_id!r} invalid knowledge_state: {state!r}")

        for flag in _BOOLEAN_FLAGS:
            val = ing.get(flag)
            if not isinstance(val, bool):
                errors.append(f"Entry {entry_id!r} field {flag} is not bool: {val!r}")

        for alias in ing.get("aliases") or []:
            alias_norm = _norm_name(alias)
            if not alias_norm:
                continue
            if alias_norm in alias_owner and alias_owner[alias_norm] != entry_id:
                errors.append(
                    f"Alias {alias!r} shared by {alias_owner[alias_norm]!r} and {entry_id!r}"
                )
            else:
                alias_owner[alias_norm] = entry_id

    return errors


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        print(f"Warning: missing input {path}", file=sys.stderr)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_india_catalog() -> Path | None:
    for path in _INDIA_CATALOG_PATHS:
        if path.exists():
            return path
    print("Warning: india_ingredients_catalog.json not found", file=sys.stderr)
    return None


def merge_all(*, dry_run: bool = False) -> dict[str, Any]:
    if not _ONTOLOGY_PATH.exists():
        raise FileNotFoundError(f"Missing ontology: {_ONTOLOGY_PATH}")

    ontology = json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))
    ingredients: list[dict[str, Any]] = list(ontology.get("ingredients") or [])
    before_count = len(ingredients)

    for ing in ingredients:
        if ing.get("knowledge_state") not in _VALID_KNOWLEDGE_STATES:
            ing["knowledge_state"] = "UNKNOWN"

    index = OntologyIndex(ingredients)
    stats: dict[str, Any] = {
        "new_entries": 0,
        "merged_into_existing": 0,
        "aliases_added": 0,
        "skipped_duplicates": 0,
        "skipped_protected": 0,
        "skipped_not_plausible": 0,
        "deduped_same_canonical": 0,
        "deduped_alias_canonical": 0,
    }

    e_catalog = _load_json(_E_NUMBER_CATALOG)
    if e_catalog:
        print("Merging e_number_catalog.json...")
        _merge_e_number_catalog(index, e_catalog, stats)

    india_path = _resolve_india_catalog()
    if india_path:
        india = _load_json(india_path)
        if india:
            print(f"Merging {india_path.name}...")
            _merge_generic_source(
                index,
                india.get("ingredients") or [],
                "india_ingredients_catalog",
                stats,
            )

    for source_name, staging_path in _STAGING_SOURCES:
        staging = _load_json(staging_path)
        if not staging:
            continue
        print(f"Merging {staging_path.name}...")
        _merge_generic_source(
            index,
            staging.get("ingredients") or [],
            source_name,
            stats,
        )

    near_duplicate_warnings = _deduplicate(index.ingredients, stats)
    validation_errors = _validate(index.ingredients)

    after_count = len(index.ingredients)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "before_count": before_count,
        "after_count": after_count,
        "new_entries": stats["new_entries"],
        "merged_into_existing": stats["merged_into_existing"],
        "aliases_added": stats["aliases_added"],
        "skipped_duplicates": stats["skipped_duplicates"],
        "skipped_protected": stats["skipped_protected"],
        "skipped_not_plausible": stats["skipped_not_plausible"],
        "deduped_same_canonical": stats["deduped_same_canonical"],
        "deduped_alias_canonical": stats["deduped_alias_canonical"],
        "validation_errors": validation_errors,
        "near_duplicate_warnings": near_duplicate_warnings,
        "dry_run": dry_run,
    }

    if not dry_run:
        ontology["ingredients"] = index.ingredients
        if "ontology_version" not in ontology:
            ontology["ontology_version"] = "1.2"
        with open(_ONTOLOGY_PATH, encoding="utf-8") as src:
            backup_text = src.read()
        with open(_BACKUP_PATH, "w", encoding="utf-8") as dst:
            dst.write(backup_text)
        os.chmod(_BACKUP_PATH, os.stat(_ONTOLOGY_PATH).st_mode)
        _ONTOLOGY_PATH.write_text(
            json.dumps(ontology, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return report


def _print_summary(report: dict[str, Any]) -> None:
    print(f"Before: {report['before_count']} ingredients")
    print(f"After:  {report['after_count']} ingredients")
    print(f"New entries:            {report['new_entries']}")
    print(f"Merged into existing:   {report['merged_into_existing']}")
    print(f"Aliases added:          {report['aliases_added']}")
    print(f"Skipped duplicates:     {report['skipped_duplicates']}")
    print(f"Skipped (protected):    {report['skipped_protected']}")
    print(f"Skipped (not plausible):  {report['skipped_not_plausible']}")
    print(f"Deduped (same canonical): {report['deduped_same_canonical']}")
    print(f"Deduped (alias=canonical): {report['deduped_alias_canonical']}")
    if report["near_duplicate_warnings"]:
        print(f"Near-duplicate warnings: {len(report['near_duplicate_warnings'])}")
        for msg in report["near_duplicate_warnings"][:10]:
            print(f"  - {msg}")
        if len(report["near_duplicate_warnings"]) > 10:
            print(f"  ... and {len(report['near_duplicate_warnings']) - 10} more")
    if report["validation_errors"]:
        print(f"Validation errors: {len(report['validation_errors'])}")
        for err in report["validation_errors"][:10]:
            print(f"  - {err}")
    elif not report.get("dry_run"):
        print(f"Wrote {_ONTOLOGY_PATH}")
        print(f"Backup: {_BACKUP_PATH}")
        print(f"Report: {_REPORT_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge all staging sources into ontology.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute merge stats without writing ontology.json",
    )
    args = parser.parse_args()

    try:
        report = merge_all(dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print("Dry run — no files written.")
    _print_summary(report)
    return 1 if report["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
