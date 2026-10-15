#!/usr/bin/env python3
"""Item 44 — stratified OFF label benchmark (ODbL).

Builds or loads ``data/item44_off_product_ids.json``, fetches ingredient texts,
evaluates 6 mechanism profiles + one combined run, writes report artifacts.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import ssl
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

try:
    import certifi

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover
    _SSL_CTX = ssl.create_default_context()

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict, to_external
from core.normalization.parser import flatten_ingredients

SEED = 44
TARGET_PER_CELL = 12  # 3 markets × 6 categories × 12 ≈ 216
MARKETS = {
    "india": ["india"],
    "us": ["united-states"],
    "uk_eu": ["united-kingdom", "france", "germany"],
}
CATEGORIES = {
    "snacks": ["snacks"],
    "sauces_condiments": ["sauces", "condiments"],
    "bakery": ["breads", "biscuits"],
    "dairy_alternatives": ["plant-based milk alternatives", "dairy substitutes"],
    "ready_meals": ["meals", "prepared meals"],
    "supplements": ["dietary supplements", "vitamins"],
}

PROFILES = {
    "vegan": {"vegan": "preference"},
    "jain": {"jain": "religious"},
    "halal": {"halal": "religious"},
    "gluten_free": {"gluten_free": "medical"},
    "peanut_allergy": {"peanut_allergy": "medical"},
    "dairy_free": {"dairy_free": "medical"},
    "combined_vegan_peanut_gluten": {
        "vegan": "preference",
        "peanut_allergy": "medical",
        "gluten_free": "medical",
    },
}

_IDS_PATH = _REPO / "data" / "item44_off_product_ids.json"
_REPORT_DIR = _BACKEND / ".local_reports"
_REPORT_JSON = _REPORT_DIR / "item44_benchmark_report.json"
_REPORT_MD = _REPORT_DIR / "item44_benchmark_report.md"


def _off_get(url: str, timeout: int = 45, retries: int = 6) -> dict:
    """Prefer requests+certifi; fall back to urllib."""
    last_exc: Exception | None = None
    headers = {"User-Agent": "IngreSure-Item44Benchmark/1.0 (research; ODbL)"}
    try:
        import requests
    except ImportError:
        requests = None  # type: ignore
    for attempt in range(retries):
        try:
            if requests is not None:
                resp = requests.get(url, headers=headers, timeout=timeout)
                if resp.status_code == 503:
                    raise RuntimeError("503")
                resp.raise_for_status()
                data = resp.json()
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                    data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise RuntimeError("OFF response not an object")
            return data
        except Exception as exc:
            last_exc = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"OFF GET failed after {retries}: {last_exc}")


def _search_codes(country_tags: list[str], category_tags: list[str], page_size: int = 40) -> list[str]:
    """OFF API v2 search (cgi/search.pl often 503)."""
    # Prefer bare country/category slugs for v2 filters.
    country = (country_tags[0] if country_tags else "").removeprefix("en:")
    category = (category_tags[0] if category_tags else "").removeprefix("en:")
    params = {
        "page_size": str(page_size),
        "page": "1",
        "fields": "code,ingredients_text,countries_tags,categories_tags",
        "sort_by": "unique_scans_n",
    }
    if country:
        params["countries_tags_en"] = country.replace("-", " ")
    if category:
        params["categories_tags_en"] = category.replace("-", " ")
    url = "https://world.openfoodfacts.org/api/v2/search?" + urllib.parse.urlencode(params)
    try:
        data = _off_get(url)
    except Exception as exc:
        print(f"search failed {country}/{category}: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, dict):
        print(f"search non-json {country}/{category}", file=sys.stderr)
        return []
    codes = []
    for p in data.get("products") or []:
        code = str(p.get("code") or "").strip()
        text = (p.get("ingredients_text") or "").strip()
        if code and text and len(text) >= 8:
            codes.append(code)
    return codes


def build_sample(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    cells = []
    all_ids: list[dict] = []
    seen: set[str] = set()
    for market, countries in MARKETS.items():
        for category, cats in CATEGORIES.items():
            pool: list[str] = []
            for ctag in countries[:2]:
                for ktag in cats[:2]:
                    try:
                        pool.extend(_search_codes([ctag], [ktag]))
                    except Exception as exc:
                        print(f"search err {market}/{category}: {exc}", file=sys.stderr)
                    time.sleep(0.8)
            # Broaden: country-only if cell empty.
            if len([c for c in dict.fromkeys(pool) if c not in seen]) < TARGET_PER_CELL:
                for ctag in countries[:1]:
                    try:
                        pool.extend(_search_codes([ctag], []))
                    except Exception as exc:
                        print(f"broad search err {market}: {exc}", file=sys.stderr)
                    time.sleep(0.8)
            pool = [c for c in dict.fromkeys(pool) if c not in seen]
            rng.shuffle(pool)
            picked = pool[:TARGET_PER_CELL]
            shortfall = max(0, TARGET_PER_CELL - len(picked))
            for code in picked:
                seen.add(code)
                all_ids.append({"code": code, "market": market, "category": category})
            cells.append(
                {
                    "market": market,
                    "category": category,
                    "n": len(picked),
                    "shortfall": shortfall,
                }
            )
            print(f"cell {market}/{category}: {len(picked)} (shortfall {shortfall})", flush=True)
    sample = {
        "seed": seed,
        "odbl_attribution": (
            "Product metadata from Open Food Facts, licensed under ODbL "
            "(https://opendatacommons.org/licenses/odbl/). Ingredient texts "
            "are not redistributed here — only product codes."
        ),
        "n_products": len(all_ids),
        "cells": cells,
        "products": all_ids,
    }
    _IDS_PATH.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
    return sample


def _fetch_product(code: str) -> dict | None:
    url = f"https://world.openfoodfacts.org/api/v2/product/{code}.json?fields=code,product_name,ingredients_text,countries_tags,categories_tags"
    try:
        data = _off_get(url)
    except Exception:
        return None
    if data.get("status") != 1:
        return None
    return data.get("product") or {}


def _layer_bucket(resolved) -> str:
    layer = getattr(resolved, "resolution_layer", "") or ""
    trusted = bool(getattr(resolved, "trusted", False))
    if layer.startswith("L1"):
        return "L1"
    if layer.startswith("L2"):
        return "L2"
    if layer.startswith("L3"):
        return "L3_trusted" if trusted else "L3_untrusted"
    if layer.startswith("L5") or "unknown" in layer:
        return "L5_unknown"
    return layer or "other"


def _raw_segments(text: str) -> list[str]:
    """Naive comma split for garbled / strip diagnostics (not the evaluator path)."""
    return [p.strip() for p in re.split(r"[,;]", text or "") if p.strip()]


def _atoms(text: str) -> tuple[list[str], dict]:
    """Return (atoms, diag). diag counts quantity noise and empty-after-strip."""
    from core.normalization.parser import _BARE_NUMBER, _PERCENT_ONLY, _TRAILING_PERCENT

    raw_segs = _raw_segments(text)
    stripped_qty = 0
    for seg in raw_segs:
        s = seg.strip()
        if _PERCENT_ONLY.match(s) or _BARE_NUMBER.match(s):
            stripped_qty += 1
        elif _TRAILING_PERCENT.search(s):
            stripped_qty += 1
    flat = flatten_ingredients(text) if text else []
    out = [str(a).strip() for a in (flat or []) if str(a).strip()]
    diag = {
        "n_raw_segments": len(raw_segs),
        "n_atoms": len(out),
        "n_quantity_tokens_stripped": stripped_qty,
    }
    return out, diag


def _coverage_curve(instance_counts: Counter) -> dict:
    """Distinct ingredients to promote for 25/50/80% of instances."""
    total = sum(instance_counts.values()) or 1
    ranked = instance_counts.most_common()
    cum = 0
    thresholds = {0.25: None, 0.50: None, 0.80: None}
    for i, (_name, n) in enumerate(ranked, start=1):
        cum += n
        frac = cum / total
        for t in thresholds:
            if thresholds[t] is None and frac >= t:
                thresholds[t] = i
    return {
        "n_distinct": len(ranked),
        "n_instances": total,
        "distinct_for_25pct_instances": thresholds[0.25],
        "distinct_for_50pct_instances": thresholds[0.50],
        "distinct_for_80pct_instances": thresholds[0.80],
    }


def _eval_list(atoms: list[str], restrictions: dict) -> tuple[str, list[dict], str | None]:
    """Return (list_verdict, per_atom rows, weakest_link name)."""
    rules = rules_module.seeded_rules()
    profile = SimpleNamespace(restrictions=restrictions)
    cis = []
    rows = []
    for atom in atoms:
        cache.clear()
        r = resolve(atom, None)
        ci = to_compliance_input(r, query_atom=atom)
        cis.append(ci)
        # per-atom aggregate under this profile
        one = evaluate([ci], profile, rules)
        v = to_external(one.verdict)
        group = r.group
        has_group = group is not None
        # derive-only NOT_SAFE: hazard present, no resolved group (L5 label-derived)
        derive_only = (
            v == "NOT_SAFE"
            and not has_group
            and bool(ci.flags)
        )
        rows.append(
            {
                "atom": atom,
                "layer": r.resolution_layer,
                "layer_bucket": _layer_bucket(r),
                "trusted": bool(ci.trusted),
                "verdict": v,
                "derive_only_not_safe": derive_only,
                "source_phrase": atom if derive_only else None,
            }
        )
    agg = evaluate(cis, profile, rules)
    list_v = to_external(agg.verdict)
    weakest = None
    if list_v != "SAFE":
        # prefer NOT_SAFE atoms, else first non-SAFE
        for prefer in ("NOT_SAFE", "UNCERTAIN"):
            hit = next((row for row in rows if row["verdict"] == prefer), None)
            if hit:
                weakest = hit["atom"]
                break
    return list_v, rows, weakest


def run_benchmark(sample: dict) -> dict:
    unparseable = 0
    garbled = 0
    garbled_reasons: Counter = Counter()
    quantity_stripped_total = 0
    products_ok = []
    layer_overall: Counter = Counter()
    layer_by_market: dict[str, Counter] = {m: Counter() for m in MARKETS}
    instance_freq: Counter = Counter()
    list_verdicts: dict[str, Counter] = {p: Counter() for p in PROFILES}
    uncertain_ings: Counter = Counter()
    derive_only: Counter = Counter()
    derive_only_detail: list[dict] = []
    weakest_links: list[dict] = []

    products = sample.get("products") or []
    for i, meta in enumerate(products):
        code = meta["code"]
        market = meta["market"]
        prod = _fetch_product(code)
        time.sleep(0.25)
        if not prod:
            unparseable += 1
            continue
        text = (prod.get("ingredients_text") or "").strip()
        if not text or len(text) < 8:
            garbled += 1
            garbled_reasons["empty_or_short_text"] += 1
            continue
        atoms, diag = _atoms(text)
        quantity_stripped_total += diag["n_quantity_tokens_stripped"]
        # Majority of raw segments were quantity noise and nothing usable remains.
        if not atoms:
            garbled += 1
            garbled_reasons["no_atoms_after_split"] += 1
            continue
        if (
            diag["n_raw_segments"] > 0
            and diag["n_quantity_tokens_stripped"] / diag["n_raw_segments"] >= 0.5
            and diag["n_atoms"] <= 1
        ):
            garbled += 1
            garbled_reasons["majority_quantity_noise"] += 1
            continue
        products_ok.append(code)
        for atom in atoms:
            cache.clear()
            r = resolve(atom, None)
            b = _layer_bucket(r)
            layer_overall[b] += 1
            layer_by_market[market][b] += 1
            instance_freq[atom.lower()] += 1

        for pname, restrictions in PROFILES.items():
            list_v, rows, weakest = _eval_list(atoms, restrictions)
            list_verdicts[pname][list_v] += 1
            if list_v == "UNCERTAIN":
                for row in rows:
                    if row["verdict"] == "UNCERTAIN":
                        uncertain_ings[row["atom"].lower()] += 1
            for row in rows:
                if row["derive_only_not_safe"]:
                    key = row["atom"].lower()
                    derive_only[key] += 1
                    derive_only_detail.append(
                        {
                            "code": code,
                            "market": market,
                            "profile": pname,
                            "source_phrase": row["source_phrase"],
                            "atom": row["atom"],
                        }
                    )
            weakest_links.append(
                {
                    "code": code,
                    "market": market,
                    "profile": pname,
                    "list_verdict": list_v,
                    "weakest_link": weakest,
                }
            )
        if (i + 1) % 20 == 0:
            print(f"evaluated {i+1}/{len(products)}", flush=True)

    def _rate(counter: Counter) -> dict:
        total = sum(counter.values()) or 1
        return {k: {"n": counter[k], "rate": round(counter[k] / total, 4)} for k in ("SAFE", "UNCERTAIN", "NOT_SAFE")}

    curve = _coverage_curve(instance_freq)
    report = {
        "seed": sample.get("seed"),
        "n_product_ids": len(products),
        "n_evaluated_lists": len(products_ok),
        "n_unparseable": unparseable,
        "n_garbled_excluded": garbled,
        "garbled_reasons": dict(garbled_reasons),
        "n_quantity_tokens_stripped": quantity_stripped_total,
        "odbl_attribution": sample.get("odbl_attribution"),
        "per_list_verdicts": {p: _rate(list_verdicts[p]) for p in PROFILES},
        "per_ingredient_resolution": {
            "overall": dict(layer_overall),
            "by_market": {m: dict(layer_by_market[m]) for m in MARKETS},
        },
        "coverage_curve": curve,
        "top_50_uncertain_ingredients": [
            {"ingredient": k, "n": n} for k, n in uncertain_ings.most_common(50)
        ],
        "top_50_derive_only_not_safe": [
            {"ingredient": k, "n": n} for k, n in derive_only.most_common(50)
        ],
        "derive_only_not_safe_with_phrase": derive_only_detail[:200],
        "weakest_link_per_list": weakest_links,
        "cells": sample.get("cells"),
        "gate_note": (
            "Any derive-only NOT_SAFE that is a false Avoid on a pantry staple "
            "→ golden + flag_derive fix before pilot."
        ),
    }
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Item 44 benchmark report",
        "",
        f"Evaluated lists: **{report['n_evaluated_lists']}** "
        f"(unparseable {unparseable}, garbled excluded {garbled}).",
        f"Quantity tokens stripped (not counted as ingredients): **{quantity_stripped_total}**.",
        f"Garbled reasons: `{json.dumps(dict(garbled_reasons))}`.",
        "",
        "## Coverage curve (distinct ingredients → instance share)",
        "",
        f"- distinct={curve['n_distinct']} instances={curve['n_instances']}",
        f"- for 25% of instances: **{curve['distinct_for_25pct_instances']}** distinct",
        f"- for 50% of instances: **{curve['distinct_for_50pct_instances']}** distinct",
        f"- for 80% of instances: **{curve['distinct_for_80pct_instances']}** distinct",
        "",
        "## Per-list verdict rates",
        "",
    ]
    for p, rates in report["per_list_verdicts"].items():
        md.append(f"### {p}")
        md.append(
            f"- SAFE {rates.get('SAFE', {}).get('rate')} "
            f"/ UNCERTAIN {rates.get('UNCERTAIN', {}).get('rate')} "
            f"/ NOT_SAFE {rates.get('NOT_SAFE', {}).get('rate')}"
        )
        md.append("")
    md += [
        "## Per-ingredient resolution (overall + by market)",
        "",
        "```",
        json.dumps(report["per_ingredient_resolution"], indent=2),
        "```",
        "",
        "## Top 20 UNCERTAIN ingredients",
        "",
    ]
    for row in report["top_50_uncertain_ingredients"][:20]:
        md.append(f"- `{row['ingredient']}` × {row['n']}")
    md += ["", "## Top 20 derive-only NOT_SAFE", ""]
    for row in report["top_50_derive_only_not_safe"][:20]:
        md.append(f"- `{row['ingredient']}` × {row['n']}")
    md.append("")
    md.append(report["gate_note"])
    _REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-sample", action="store_true", help="fetch stratified OFF codes")
    ap.add_argument("--run", action="store_true", help="evaluate sample")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    if not args.build_sample and not args.run:
        ap.error("pass --build-sample and/or --run")

    if args.build_sample:
        print("building stratified sample…", flush=True)
        sample = build_sample(args.seed)
    else:
        sample = json.loads(_IDS_PATH.read_text(encoding="utf-8"))
        print(f"loaded sample n={sample.get('n_products')}", flush=True)

    if args.run:
        report = run_benchmark(sample)
        print(
            json.dumps(
                {
                    "n_evaluated": report["n_evaluated_lists"],
                    "path": str(_REPORT_JSON),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
