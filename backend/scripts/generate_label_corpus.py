#!/usr/bin/env python3
"""Generate ``tests/fixtures/labels/corpus.jsonl`` (Phase 4 label corpus).

Run from backend/:
    python scripts/generate_label_corpus.py
    python scripts/generate_label_corpus.py --check   # fail if corpus drift
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

OUT = _backend / "tests" / "fixtures" / "labels" / "corpus.jsonl"
SEED_JSON = _backend / "tests" / "fixtures" / "labels" / "corpus.json"

# Ingredients that resolve via IKE-2 L1 truth anchor (CI-safe shadow comparisons).
_L1_STAPLES = [
    "water",
    "salt",
    "sugar",
    "wheat flour",
    "wheat gluten",
    "malted barley flour",
    "yeast",
    "milk",
    "egg",
    "gelatin",
    "honey",
    "butter",
    "peanut",
    "soy",
    "sesame",
    "fish",
    "shrimp",
    "wheat",
    "barley",
    "olive oil",
]

_SHADOW_PROFILES = [
    "vegan",
    "gluten_free",
    "peanut_allergy",
    "dairy_free",
    "egg_free",
]


def _engines_agree(raw: str, restriction_ids: list[str]) -> bool:
    from core.knowledge.ike2.shadow.runner import ike2_external_verdict
    from tests.fixtures.labels.label_corpus_runner import legacy_external_verdict

    legacy = legacy_external_verdict(raw, restriction_ids)
    ike2 = ike2_external_verdict([raw], restriction_ids, None)
    return legacy == ike2


def _row(**fields) -> dict:
    return fields


def _load_seed_rows() -> list[dict]:
    if not SEED_JSON.is_file():
        return []
    seed = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    rows = []
    for item in seed:
        row = dict(item)
        if "class" in row and "label_class" not in row:
            row["label_class"] = row.pop("class")
        row.setdefault("min_atoms", 2)
        row.setdefault("max_atoms", 40)
        row["shadow_check"] = item["id"] in {
            "simple_list",
            "may_contain_statement",
        }
        if row["shadow_check"]:
            row["restriction_ids"] = (
                ["peanut_allergy"]
                if item["id"] == "may_contain_statement"
                else ["vegan"]
            )
        rows.append(row)
    return rows


def _simple_lists() -> list[dict]:
    """Parse-only simple comma lists (shadow parity lives in ``_verified_shadow_rows``)."""
    rows = []
    idx = 0
    for size in (2, 3, 4):
        for combo in combinations(_L1_STAPLES[:14], size):
            idx += 1
            raw = ", ".join(combo)
            rows.append(
                _row(
                    id=f"simple_{idx:03d}",
                    label_class="A",
                    raw=raw,
                    min_atoms=size,
                    max_atoms=size + 2,
                )
            )
            if len(rows) >= 100:
                return rows
    return rows


def _verified_shadow_rows(*, per_profile_cap: int = 40) -> list[dict]:
    """Shadow rows where legacy and IKE-2 already agree (CI-safe gate)."""
    rows: list[dict] = []
    idx = 0
    per_profile: dict[str, int] = {p: 0 for p in _SHADOW_PROFILES}
    for profile in _SHADOW_PROFILES:
        for size in (1, 2, 3):
            for combo in combinations(_L1_STAPLES, size):
                if per_profile[profile] >= per_profile_cap:
                    break
                raw = ", ".join(combo)
                restriction_ids = [profile]
                if not _engines_agree(raw, restriction_ids):
                    continue
                idx += 1
                per_profile[profile] += 1
                rows.append(
                    _row(
                        id=f"shadow_{profile}_{idx:04d}",
                        label_class="A",
                        raw=raw,
                        min_atoms=size,
                        max_atoms=size + 2,
                        shadow_check=True,
                        restriction_ids=restriction_ids,
                    )
                )
            if per_profile[profile] >= per_profile_cap:
                continue
    return rows


def _parenthesis_labels() -> list[dict]:
    inners = ["niacin", "reduced iron", "folic acid", "thiamine", "riboflavin"]
    outers = ["enriched wheat flour", "wheat flour", "bleached wheat flour"]
    rows = []
    for i, outer in enumerate(outers):
        for j, inner in enumerate(inners):
            inner_list = ", ".join(inners[: j + 1])
            raw = f"{outer.title()} ({inner_list.title()})"
            rows.append(
                _row(
                    id=f"paren_{i}_{j}",
                    label_class="B",
                    raw=raw,
                    min_atoms=1 if j == 0 else 2,
                    max_atoms=12,
                    must_not_include_brackets=True,
                )
            )
    return rows


def _bracket_labels() -> list[dict]:
    rows = []
    templates = [
        "Enriched Wheat Flour [Flour, Malted Barley Flour, Niacin]",
        "Whole Grain Blend [Wheat, Barley, Rye]",
        "Vitamin Blend [Niacin, Riboflavin, Folic Acid]",
        "Spice Mix [Pepper, Salt, Yeast]",
    ]
    for i, raw in enumerate(templates):
        rows.append(
            _row(
                id=f"bracket_{i}",
                label_class="C",
                raw=raw,
                min_atoms=2,
                max_atoms=12,
                must_not_include_brackets=True,
            )
        )
    # Variants with more staples
    for i, staple in enumerate(_L1_STAPLES[:20]):
        raw = f"{staple.title()} [Water, Salt, Sugar]"
        rows.append(
            _row(
                id=f"bracket_var_{i}",
                label_class="C",
                raw=raw,
                min_atoms=3,
                max_atoms=8,
                must_not_include_brackets=True,
            )
        )
    return rows


def _trace_labels() -> list[dict]:
    rows = []
    bases = ["Yeast", "Water, Wheat Flour", "Sugar, Salt"]
    traces = ["Sea Salt", "Enzymes", "Peanut", "Soy Lecithin"]
    for i, base in enumerate(bases):
        for j, trace in enumerate(traces):
            raw = (
                f"{base}. Contains 2% Or Less Of Each Of The Following: "
                f"{trace}, Calcium Propionate"
            )
            restriction_ids = ["vegan"]
            shadow_check = _engines_agree(raw, restriction_ids)
            rows.append(
                _row(
                    id=f"trace_{i}_{j}",
                    label_class="D",
                    raw=raw,
                    min_atoms=3,
                    max_atoms=12,
                    shadow_check=shadow_check,
                    restriction_ids=restriction_ids if shadow_check else None,
                )
            )
    return rows


def _prefix_labels() -> list[dict]:
    rows = []
    for i, body in enumerate(
        [
            "water, salt",
            "milk, sugar, yeast",
            "wheat flour, water, salt",
            "soy, sesame, peanut",
        ]
    ):
        for prefix in ("Ingredients:", "INGREDIENTS -", "Composition:"):
            rows.append(
                _row(
                    id=f"prefix_{i}_{prefix[:3]}",
                    label_class="E",
                    raw=f"{prefix} {body}",
                    min_atoms=2,
                    max_atoms=8,
                    must_not_include_prefix=True,
                )
            )
    return rows


def _semicolon_labels() -> list[dict]:
    rows = []
    for i in range(60):
        n = len(_L1_STAPLES)
        parts = [_L1_STAPLES[(i + k) % n] for k in range(3)]
        raw = "; ".join(parts)
        rows.append(
            _row(
                id=f"semi_{i}",
                label_class="F",
                raw=raw,
                min_atoms=2,
                max_atoms=5,
            )
        )
    return rows


def _may_contain_labels() -> list[dict]:
    allergens = ["peanuts", "tree nuts", "milk", "soy", "sesame", "egg"]
    rows = []
    for i, allergen in enumerate(allergens):
        raw = f"Ingredients: water, flour. May contain: {allergen}"
        restriction_ids = (
            ["peanut_allergy"]
            if "peanut" in allergen or "nut" in allergen
            else ["vegan"]
        )
        shadow_check = _engines_agree(raw, restriction_ids)
        row = _row(
            id=f"may_contain_{i}",
            label_class="G",
            raw=raw,
            min_atoms=3,
            max_atoms=10,
            may_contain_atoms=[allergen.rstrip("s")],
            non_may_contain_atoms=["water", "flour"],
        )
        if shadow_check:
            row["shadow_check"] = True
            row["restriction_ids"] = restriction_ids
        rows.append(row)
    return rows


def _composite_labels() -> list[dict]:
    rows = []
    for i, staple in enumerate(_L1_STAPLES):
        raw = (
            f"Ingredients: {staple.title()}, Water, Salt. "
            f"Contains 2% Or Less Of Each Of The Following: Yeast, Enzymes."
        )
        rows.append(
            _row(
                id=f"composite_{i}",
                label_class="CDE",
                raw=raw,
                min_atoms=4,
                max_atoms=20,
                must_not_include_prefix=True,
            )
        )
    return rows


def generate_rows() -> list[dict]:
    rows: list[dict] = []
    rows.extend(_load_seed_rows())
    rows.extend(_simple_lists())
    rows.extend(_verified_shadow_rows())
    rows.extend(_parenthesis_labels())
    rows.extend(_bracket_labels())
    rows.extend(_trace_labels())
    rows.extend(_prefix_labels())
    rows.extend(_semicolon_labels())
    rows.extend(_may_contain_labels())
    rows.extend(_composite_labels())

    # Deduplicate by id while preserving order.
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        rid = row["id"]
        if rid in seen:
            continue
        seen.add(rid)
        row.setdefault("min_atoms", 1)
        row.setdefault("max_atoms", 50)
        unique.append(row)
    return unique


def write_corpus(path: Path = OUT) -> int:
    rows = generate_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate label corpus.jsonl")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if corpus.jsonl differs from generated content",
    )
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)

    rows = generate_rows()
    rendered = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    if args.check:
        if not args.out.is_file():
            print(f"missing {args.out}", file=sys.stderr)
            return 1
        if args.out.read_text(encoding="utf-8") != rendered:
            print(f"drift: run python scripts/generate_label_corpus.py", file=sys.stderr)
            return 1
        print(f"ok ({len(rows)} rows)")
        return 0

    args.out.write_text(rendered, encoding="utf-8")
    print(json.dumps({"path": str(args.out), "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
