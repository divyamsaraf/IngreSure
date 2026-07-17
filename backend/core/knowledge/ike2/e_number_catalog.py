"""Shared E-number catalog loading, tiering, and IKE-2 flag mapping.

Single source of truth: ``data/e_number_catalog.json``. Used by verify/generate
scripts and ``adapt_e_number`` for bulk inject.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, _alcohol_role, _map_nut_source
from core.normalization.normalizer import (
    is_plausible_e_number_code,
    normalize_ingredient_key,
    parse_e_number,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CATALOG_PATH = _REPO_ROOT / "data" / "e_number_catalog.json"

# Hand-curated truth-anchor keys that must not contradict catalog (subset with E-codes).
_TRUTH_ANCHOR_E_CHECKS: dict[str, dict[str, Any]] = {
    "e120": {"insect_derived": True, "animal_origin": True},
    "e441": {"animal_origin": True},
    "e631": {"animal_origin": True},
    "e901": {"insect_derived": True, "animal_origin": True},
    "e904": {"insect_derived": True, "animal_origin": True},
    "e966": {"dairy_source": True, "animal_origin": True},
    "e1105": {"egg_source": True, "animal_origin": True},
}

# Obvious allergen expectations for animal-origin insect additives.
_OBVIOUS_ALLERGEN_CHECKS = {
    "e120": {"insect_derived": True},
}


def catalog_path(path: Optional[str | Path] = None) -> Path:
    return Path(path) if path else DEFAULT_CATALOG_PATH


def load_catalog(path: Optional[str | Path] = None) -> list[dict]:
    with open(catalog_path(path)) as fh:
        data = json.load(fh)
    return list(data.get("entries") or [])


def normalize_e_code(e_code: str) -> str:
    """Normalize to lowercase compact form: e120, e100i, e322 (from e322(ii))."""
    compact = re.sub(r"\s+", "", str(e_code).strip())
    # Parenthetical variant suffixes on labels: E322(ii) -> E322, E100(i) -> E100i.
    paren = re.match(r"^(e\d{3,4})\(([^)]+)\)$", compact, re.IGNORECASE)
    if paren:
        base, inner = paren.group(1).lower(), paren.group(2).strip().lower()
        if len(inner) == 1 and inner.isalpha():
            compact = f"{base}{inner}"
        else:
            compact = base
    parsed = parse_e_number(compact)
    if not parsed:
        return normalize_ingredient_key(e_code)
    num, suffix = parsed
    return f"e{num}{suffix}" if suffix else f"e{num}"


def _slug_variants(key: str) -> list[str]:
    """Singular/plural slug variants for merge_into resolution."""
    if not key:
        return []
    variants = {key}
    if key.endswith("s") and len(key) > 1:
        variants.add(key[:-1])
    else:
        variants.add(key + "s")
    return list(variants)


def classify_tier(entry: dict) -> str:
    """Tier A = unambiguous; Tier B = has uncertainty_flags (fail-closed for diet rules)."""
    flags = entry.get("uncertainty_flags") or []
    return "B" if flags else "A"


def _merge_lookup_keys(raw: str) -> list[str]:
    """Normalize merge_into targets for slug / underscore / plural matching."""
    key = normalize_ingredient_key(str(raw).replace("_", " "))
    variants = {key, key.replace(" ", "_"), key.replace("_", " ")}
    out: list[str] = []
    for variant in variants:
        out.extend(_slug_variants(variant))
    return out


def resolve_merge_target(
    entry: dict,
    by_e_code: dict[str, dict],
    by_canonical: dict[str, dict],
    by_alias: Optional[dict[str, dict]] = None,
) -> dict:
    """Follow merge_into to the canonical catalog row."""
    target = entry.get("merge_into")
    if not target:
        return entry
    raw = str(target).strip()
    if is_plausible_e_number_code(raw) or re.match(r"^e\d", raw, re.IGNORECASE):
        code = normalize_e_code(raw)
        if code in by_e_code:
            return by_e_code[code]
    for candidate in _merge_lookup_keys(raw):
        if by_alias and candidate in by_alias:
            return by_alias[candidate]
        if candidate in by_canonical:
            return by_canonical[candidate]
        if candidate in by_e_code:
            return by_e_code[candidate]
        for canon_key, row in by_canonical.items():
            if canon_key.startswith(candidate + " ") or canon_key.startswith(candidate + "-"):
                return row
    return entry


def entry_to_ike2_row(entry: dict, *, tier: Optional[str] = None) -> dict:
    """Map a catalog entry to ike2_ingredient_groups-shaped row."""
    tier = tier or classify_tier(entry)
    raw = dict(entry)
    row = {flag: bool(raw.get(flag, False)) for flag in BOOL_FLAGS}
    _map_nut_source(raw, row)

    for extra in (
        "peanut_source", "tree_nut_source", "fish_source", "shellfish_source",
        "mustard_source", "celery_source", "lupin_source", "sulphite_source",
    ):
        if raw.get(extra):
            row[extra] = True

    canonical = normalize_ingredient_key(raw.get("canonical_name") or "")
    row["canonical_name"] = canonical
    row["animal_species"] = raw.get("animal_species")
    row["alcohol_content"] = raw.get("alcohol_content")
    row["alcohol_role"] = raw.get("alcohol_role") or _alcohol_role(raw)
    row["uncertainty_flags"] = list(raw.get("uncertainty_flags") or [])
    row["ike2_tier"] = tier
    row["verdict_cap"] = "WARN" if tier == "B" else raw.get("verdict_cap")
    row["knowledge_state"] = "AUTO_CLASSIFIED" if tier == "B" else "LOCKED"
    row["primary_source_url"] = raw.get("primary_source_url") or (
        "https://github.com/IngreSure/IngreSure/blob/main/data/e_number_catalog.json"
    )
    row["e_code"] = normalize_e_code(raw.get("e_code") or "")
    return row


def _is_e_alias(alias: str) -> bool:
    return is_plausible_e_number_code(alias) or bool(re.match(r"^e\d", normalize_ingredient_key(alias)))


def build_index(entries: list[dict]) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    by_e_code: dict[str, dict] = {}
    by_canonical: dict[str, dict] = {}
    by_alias: dict[str, dict] = {}
    for entry in entries:
        code = normalize_e_code(entry.get("e_code") or "")
        if code:
            by_e_code[code] = entry
        canon = normalize_ingredient_key(entry.get("canonical_name") or "")
        if canon:
            by_canonical[canon] = entry
        for alias in [entry.get("e_code"), entry.get("canonical_name")] + list(entry.get("aliases") or []):
            if not alias:
                continue
            for norm in _merge_lookup_keys(str(alias)):
                by_alias.setdefault(norm, entry)
    return by_e_code, by_canonical, by_alias


def build_anchor_facts(entries: list[dict]) -> dict[str, dict]:
    """Build normalized alias -> anchor fact dict for truth_anchor_e_numbers.json."""
    by_e_code, by_canonical, by_alias = build_index(entries)
    facts: dict[str, dict] = {}

    def _register(key: str, fact: dict, *, alias_type: str = "common") -> None:
        if alias_type == "e_number" or _is_e_alias(key):
            norm = normalize_e_code(key)
        else:
            norm = normalize_ingredient_key(key)
        if not norm:
            return
        payload = {
            "canonical_name": fact["canonical_name"],
            "flags": fact["flags"],
            "knowledge_state": fact["knowledge_state"],
            "alias_type": alias_type,
        }
        if fact.get("verdict_cap"):
            payload["verdict_cap"] = fact["verdict_cap"]
        if fact.get("uncertainty_flags"):
            payload["uncertainty_flags"] = fact["uncertainty_flags"]
        facts[norm] = payload

    for entry in entries:
        resolved = resolve_merge_target(entry, by_e_code, by_canonical, by_alias)
        tier = classify_tier(resolved)
        row = entry_to_ike2_row(resolved, tier=tier)
        flags = {k: row[k] for k in BOOL_FLAGS}
        flags["animal_species"] = row.get("animal_species")
        flags["alcohol_content"] = row.get("alcohol_content")
        flags["alcohol_role"] = row.get("alcohol_role")
        if row.get("verdict_cap"):
            flags["verdict_cap"] = row["verdict_cap"]
        if row.get("uncertainty_flags"):
            flags["uncertainty_flags"] = row["uncertainty_flags"]

        fact = {
            "canonical_name": row["canonical_name"],
            "flags": flags,
            "knowledge_state": row["knowledge_state"],
            "verdict_cap": row.get("verdict_cap"),
            "uncertainty_flags": row.get("uncertainty_flags") or [],
        }

        for alias in entry.get("aliases") or []:
            atype = "e_number" if _is_e_alias(alias) else "common"
            _register(alias, fact, alias_type=atype)

        canon = normalize_ingredient_key(entry.get("canonical_name") or "")
        if canon:
            _register(canon, fact, alias_type="common")

        e_code = normalize_e_code(entry.get("e_code") or "")
        if e_code:
            _register(e_code, fact, alias_type="e_number")

    return facts


def layer1_records(entries: list[dict]) -> list[dict]:
    """Bulk-inject-shaped records with alias metadata."""
    by_e_code, by_canonical, by_alias = build_index(entries)
    records = []
    for entry in entries:
        resolved = resolve_merge_target(entry, by_e_code, by_canonical, by_alias)
        tier = classify_tier(resolved)
        row = entry_to_ike2_row(resolved, tier=tier)
        aliases_meta = []
        seen = set()
        for alias in [entry.get("e_code")] + list(entry.get("aliases") or []) + [entry.get("canonical_name")]:
            if not alias:
                continue
            norm = normalize_ingredient_key(str(alias))
            if not norm or norm in seen:
                continue
            seen.add(norm)
            atype = "e_number" if _is_e_alias(str(alias)) else "common"
            aliases_meta.append({"normalized_alias": norm, "alias_type": atype, "region": None})
        records.append({
            **{k: row[k] for k in BOOL_FLAGS},
            "canonical_name": row["canonical_name"],
            "animal_species": row.get("animal_species"),
            "alcohol_content": row.get("alcohol_content"),
            "alcohol_role": row.get("alcohol_role"),
            "uncertainty_flags": row.get("uncertainty_flags") or [],
            "knowledge_state": row["knowledge_state"],
            "verdict_cap": row.get("verdict_cap"),
            "primary_source_url": row.get("primary_source_url"),
            "e_code": row.get("e_code"),
            "ike2_tier": tier,
            "aliases_meta": aliases_meta,
        })
    return records


def truth_anchor_e_checks() -> dict[str, dict[str, Any]]:
    return dict(_TRUTH_ANCHOR_E_CHECKS)
