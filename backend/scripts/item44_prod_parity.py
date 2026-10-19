#!/usr/bin/env python3
"""Parity: held-out 216 OFF lists × 3 profiles, local TestClient vs production API.

Writes ``backend/.local_reports/item44_prod_parity.json``.
Throttles production calls (~50/min) so default RATE_LIMIT_API_V1_DEFAULT holds.
No API key — production gate is currently inactive (ENVIRONMENT ≠ production).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

_HELD = _REPO / "data" / "item44_off_product_ids.json"
_CACHE = _BACKEND / ".local_reports" / "item44_off_product_cache.json"
_OUT = _BACKEND / ".local_reports" / "item44_prod_parity.json"

_PROFILES = (
    ("vegan", ["vegan"]),
    ("gluten_free", ["gluten_free"]),
    ("peanut_allergy", ["peanut_allergy"]),
)

_DEFAULT_PROD = "https://ingresure-api.gleeze.com"


def _cache_by_code() -> dict[str, str]:
    if not _CACHE.exists():
        return {}
    raw = json.loads(_CACHE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        code = str(v.get("code") or k.split("|", 1)[0]).strip()
        text = (v.get("ingredients_text") or "").strip()
        if code and text and code not in out:
            out[code] = text
    return out


def _classify_diff(local: dict, prod: dict) -> str:
    """Heuristic bucket for a local≠prod pair."""
    lp = local.get("parsed_ingredients") or []
    pp = prod.get("parsed_ingredients") or []
    if lp != pp:
        return "parser"
    lt = set(local.get("verdict", {}).get("triggered_ingredients") or [])
    pt = set(prod.get("verdict", {}).get("triggered_ingredients") or [])
    if lt != pt and local.get("verdict", {}).get("status") != prod.get("verdict", {}).get(
        "status"
    ):
        # Same parse, different triggers → knowledge / config
        return "data"
    if local.get("verdict", {}).get("status") != prod.get("verdict", {}).get("status"):
        return "config"
    return "data"


def _local_eval(client: TestClient, raw: str, rids: list[str]) -> dict:
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": raw, "restriction_ids": rids},
    )
    r.raise_for_status()
    return r.json()


def _prod_eval(base: str, raw: str, rids: list[str], api_key: str | None) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    body = json.dumps({"ingredients_text": raw, "restriction_ids": rids}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/api/v1/evaluate-product",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod-base", default=os.environ.get("PROD_API_BASE", _DEFAULT_PROD))
    ap.add_argument("--api-key", default=os.environ.get("PROD_API_KEY") or None)
    ap.add_argument("--limit", type=int, default=0, help="Max products (0=all)")
    ap.add_argument("--sleep", type=float, default=1.2, help="Seconds between prod calls")
    ap.add_argument("--offset", type=int, default=0)
    args = ap.parse_args()

    held = json.loads(_HELD.read_text(encoding="utf-8"))["products"]
    cache = _cache_by_code()
    client = TestClient(app)

    rows = []
    missing = 0
    errors = 0
    agree = Counter()
    diff_class = Counter()

    products = held[args.offset :]
    if args.limit:
        products = products[: args.limit]

    for i, meta in enumerate(products):
        code = meta["code"]
        raw = cache.get(code)
        if not raw:
            missing += 1
            continue
        for profile_name, rids in _PROFILES:
            try:
                local = _local_eval(client, raw, rids)
            except Exception as exc:  # noqa: BLE001
                errors += 1
                rows.append(
                    {
                        "code": code,
                        "profile": profile_name,
                        "error": f"local:{exc}",
                    }
                )
                continue
            try:
                prod = _prod_eval(args.prod_base, raw, rids, args.api_key)
            except urllib.error.HTTPError as exc:
                errors += 1
                body = exc.read().decode()[:300] if exc.fp else ""
                rows.append(
                    {
                        "code": code,
                        "profile": profile_name,
                        "error": f"prod_http:{exc.code}:{body}",
                    }
                )
                time.sleep(args.sleep)
                continue
            except Exception as exc:  # noqa: BLE001
                errors += 1
                rows.append(
                    {
                        "code": code,
                        "profile": profile_name,
                        "error": f"prod:{exc}",
                    }
                )
                time.sleep(args.sleep)
                continue

            ls = local.get("verdict", {}).get("status")
            ps = prod.get("verdict", {}).get("status")
            same = ls == ps
            agree["agree" if same else "disagree"] += 1
            entry = {
                "code": code,
                "profile": profile_name,
                "local_status": ls,
                "prod_status": ps,
                "agree": same,
                "local_parsed_n": len(local.get("parsed_ingredients") or []),
                "prod_parsed_n": len(prod.get("parsed_ingredients") or []),
            }
            if not same:
                kind = _classify_diff(local, prod)
                diff_class[kind] += 1
                entry["diff_class"] = kind
                entry["local_triggered"] = local.get("verdict", {}).get(
                    "triggered_ingredients"
                )
                entry["prod_triggered"] = prod.get("verdict", {}).get(
                    "triggered_ingredients"
                )
            rows.append(entry)
            time.sleep(args.sleep)

        if (i + 1) % 20 == 0:
            print(
                f"progress {i+1}/{len(products)} agree={dict(agree)} diffs={dict(diff_class)}",
                flush=True,
            )

    report = {
        "prod_base": args.prod_base,
        "api_key_sent": bool(args.api_key),
        "n_products_requested": len(products),
        "n_missing_text": missing,
        "n_errors": errors,
        "agree": dict(agree),
        "diff_class": dict(diff_class),
        "rows": rows,
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in report if k != "rows"}, indent=2))
    print("out", _OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
