#!/usr/bin/env python3
"""Verify e_number_catalog.json against IKE-2 constraints and cross-sources.

Outputs data/e_number_verification_report.json. Use --fail-on-error for CI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.knowledge.ike2.e_number_catalog import (  # noqa: E402
    _merge_lookup_keys,
    build_index,
    classify_tier,
    entry_to_ike2_row,
    load_catalog,
    normalize_e_code,
    resolve_merge_target,
    truth_anchor_e_checks,
)
from core.knowledge.ike2.etl.validate import validate_rows
from core.normalization.normalizer import is_plausible_e_number_code, normalize_ingredient_key, parse_e_number

DEFAULT_CATALOG = _repo / "data" / "e_number_catalog.json"
DEFAULT_REPORT = _repo / "data" / "e_number_verification_report.json"
OFF_LAYER1 = _repo / "data" / "layer1_off_taxonomy.json"
WIKIDATA_LAYER1 = _repo / "data" / "layer1_wikidata.json"
FSSAI_LAYER1 = _repo / "data" / "layer1_fssai.json"
FSSAI_RAW = _repo / "data" / "raw" / "fssai" / "permitted_additives.json"


def _load_e_codes_from_layer1(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("ingredients", [])
    codes: set[str] = set()
    for item in items:
        for val in [item.get("canonical_name", "")] + list(item.get("aliases") or []):
            if is_plausible_e_number_code(str(val)):
                codes.add(normalize_e_code(str(val)))
    return codes


def _load_fssai_e_codes() -> set[str]:
    codes: set[str] = set()
    if FSSAI_RAW.exists():
        data = json.loads(FSSAI_RAW.read_text(encoding="utf-8"))
        for row in data if isinstance(data, list) else data.get("additives", []):
            for key in ("e_number", "ins_number", "code"):
                val = row.get(key)
                if val and is_plausible_e_number_code(str(val)):
                    codes.add(normalize_e_code(str(val)))
    if FSSAI_LAYER1.exists():
        codes |= _load_e_codes_from_layer1(FSSAI_LAYER1)
    return codes


def verify(entries: list[dict]) -> dict[str, Any]:
    by_e_code, by_canonical, by_alias = build_index(entries)
    errors: list[dict] = []
    warnings: list[dict] = []
    tier_a = tier_b = 0

    seen_codes: dict[str, str] = {}
    seen_canonical: dict[str, str] = {}

    for entry in entries:
        e_code = entry.get("e_code", "")
        code_key = normalize_e_code(e_code)

        if not is_plausible_e_number_code(e_code):
            errors.append({"e_code": e_code, "check": "e_code_format", "message": "invalid E-code"})
            continue

        if code_key in seen_codes:
            errors.append({"e_code": e_code, "check": "duplicate_e_code", "message": f"duplicate of {seen_codes[code_key]}"})
        else:
            seen_codes[code_key] = e_code

        resolved = resolve_merge_target(entry, by_e_code, by_canonical, by_alias)
        canonical = normalize_ingredient_key(resolved.get("canonical_name", ""))
        if canonical in seen_canonical and seen_canonical[canonical] != e_code:
            warnings.append({
                "e_code": e_code,
                "check": "shared_canonical",
                "message": f"canonical {canonical} also used by {seen_canonical[canonical]}",
            })
        else:
            seen_canonical.setdefault(canonical, e_code)

        merge_into = entry.get("merge_into")
        if merge_into:
            mt = str(merge_into).strip()
            mt_keys = set(_merge_lookup_keys(mt)) | {normalize_e_code(mt)}
            alias_keys: set[str] = set()
            for alias in [entry.get("canonical_name"), entry.get("e_code")] + list(entry.get("aliases") or []):
                if alias:
                    alias_keys.update(_merge_lookup_keys(str(alias)))
            if normalize_e_code(mt) == code_key or mt_keys & alias_keys:
                pass
            elif resolved is entry:
                if is_plausible_e_number_code(mt) or parse_e_number(mt):
                    errors.append({
                        "e_code": e_code,
                        "check": "merge_into_target",
                        "message": f"merge_into E-code {merge_into!r} not in catalog",
                    })
                else:
                    errors.append({
                        "e_code": e_code,
                        "check": "merge_into_unresolved",
                        "message": f"merge_into slug {merge_into!r} did not resolve",
                    })

        row = entry_to_ike2_row(resolved)
        _, rejects = validate_rows([row])
        if rejects:
            errors.append({
                "e_code": e_code,
                "check": "check_mirror",
                "message": rejects[0].get("violated_constraint"),
            })

        tier = classify_tier(resolved)
        if tier == "B":
            tier_b += 1
            if not (resolved.get("uncertainty_flags") or []):
                errors.append({"e_code": e_code, "check": "tier_b_flags", "message": "Tier B without uncertainty_flags"})
            uflags = " ".join(resolved.get("uncertainty_flags") or []).lower()
            if resolved.get("soy_source") and "soy" in uflags:
                errors.append({
                    "e_code": e_code,
                    "check": "tier_b_contradiction",
                    "message": "Tier B has soy_source=true with soy-related uncertainty_flags",
                })
            if resolved.get("animal_origin") and any(
                token in uflags
                for token in ("animal", "plant", "synthetic", "poultry", "hog")
            ):
                errors.append({
                    "e_code": e_code,
                    "check": "tier_b_contradiction",
                    "message": "Tier B has animal_origin=true with source ambiguity uncertainty_flags",
                })
        else:
            tier_a += 1

        for anchor_key, expected in truth_anchor_e_checks().items():
            if normalize_e_code(anchor_key) != code_key:
                continue
            for flag, val in expected.items():
                if resolved.get(flag) != val:
                    errors.append({
                        "e_code": e_code,
                        "check": "truth_anchor_conflict",
                        "message": f"{flag}: expected {val}, got {resolved.get(flag)}",
                    })

    catalog_codes = set(seen_codes)
    off_codes = _load_e_codes_from_layer1(OFF_LAYER1)
    wd_codes = _load_e_codes_from_layer1(WIKIDATA_LAYER1)
    fssai_codes = _load_fssai_e_codes()

    if off_codes - catalog_codes:
        warnings.append({
            "check": "off_cross_ref",
            "message": f"{len(off_codes - catalog_codes)} E-codes in OFF not in catalog",
            "sample": sorted(off_codes - catalog_codes)[:20],
        })
    if catalog_codes - off_codes:
        warnings.append({
            "check": "off_cross_ref",
            "message": f"{len(catalog_codes - off_codes)} catalog E-codes not in OFF",
            "sample": sorted(catalog_codes - off_codes)[:20],
        })
    if catalog_codes & wd_codes:
        warnings.append({
            "check": "wikidata_cross_ref",
            "message": f"{len(catalog_codes & wd_codes)} E-codes overlap Wikidata layer1",
        })
    if fssai_codes - catalog_codes:
        warnings.append({
            "check": "fssai_cross_ref",
            "message": f"{len(fssai_codes - catalog_codes)} FSSAI codes not in catalog",
            "sample": sorted(fssai_codes - catalog_codes)[:20],
        })

    return {
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "entries": len(entries),
            "tier_a": tier_a,
            "tier_b": tier_b,
            "merge_into": sum(1 for e in entries if e.get("merge_into")),
            "catalog_e_codes": len(catalog_codes),
            "off_e_codes": len(off_codes),
            "wikidata_e_codes": len(wd_codes),
            "fssai_e_codes": len(fssai_codes),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify E-number catalog for IKE-2")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    report = verify(load_catalog(args.catalog))
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["stats"], indent=2))
    return 1 if args.fail_on_error and report["stats"]["error_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
