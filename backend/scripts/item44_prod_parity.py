#!/usr/bin/env python3
"""Parity: held-out OFF lists × 3 profiles, same-seed reference vs candidate API.

Hard gates (always):
  - zero candidate-SAFE where the reference is NOT_SAFE or UNCERTAIN
  - zero 5xx

95% agreement is a gate only with ``--same-seed`` (reference and candidate
share the ontology seed; production will not have the ~6,800 bulk groups).

Writes ``backend/.local_reports/item44_prod_parity.json``.
Throttles production calls (~50/min) so default RATE_LIMIT_API_V1_DEFAULT holds.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

try:
    import certifi

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _SSL_CTX = ssl.create_default_context()

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


_UNSAFE = {"NOT_SAFE", "AVOID", "UNCERTAIN", "CHECK", "WARN"}


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
    with urllib.request.urlopen(req, timeout=90, context=_SSL_CTX) as resp:
        return json.loads(resp.read().decode())


def _load_reference(path: Path) -> dict[tuple[str, str], dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("rows") if isinstance(raw, dict) else raw
    out: dict[tuple[str, str], dict] = {}
    for row in rows or []:
        if not isinstance(row, dict) or row.get("error"):
            continue
        code = str(row.get("code") or "")
        profile = str(row.get("profile") or "")
        status = row.get("status") or row.get("local_status") or row.get("ref_status")
        if code and profile and status:
            out[(code, profile)] = row
            out[(code, profile)]["status"] = status
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod-base", default=os.environ.get("PROD_API_BASE", _DEFAULT_PROD))
    ap.add_argument("--api-key", default=os.environ.get("PROD_API_KEY") or None)
    ap.add_argument("--limit", type=int, default=0, help="Max products (0=all)")
    ap.add_argument("--sleep", type=float, default=1.2, help="Seconds between prod calls")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument(
        "--reference-json",
        type=Path,
        default=None,
        help="Same-seed reference run (from --write-reference). Required for a valid 95% bar.",
    )
    ap.add_argument(
        "--write-reference",
        type=Path,
        default=None,
        help="Write local TestClient results as a reference run (use on ontology-seed DB only).",
    )
    ap.add_argument(
        "--same-seed",
        action="store_true",
        help="Reference and candidate share the ontology seed. Enables the 95% agreement gate.",
    )
    args = ap.parse_args()

    held = json.loads(_HELD.read_text(encoding="utf-8"))["products"]
    cache = _cache_by_code()
    client = None if args.reference_json else TestClient(app)
    ref_index = _load_reference(args.reference_json) if args.reference_json else {}
    reference_rows = []

    rows = []
    missing = 0
    errors = 0
    n_5xx = 0
    unsafe_safe = 0
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
                if args.reference_json:
                    hit = ref_index.get((code, profile_name))
                    if not hit:
                        missing += 1
                        continue
                    local = {
                        "verdict": {"status": hit.get("status"), "triggered_ingredients": hit.get("triggered")},
                        "parsed_ingredients": hit.get("parsed_ingredients") or [],
                    }
                else:
                    local = _local_eval(client, raw, rids)
                    if args.write_reference:
                        reference_rows.append(
                            {
                                "code": code,
                                "profile": profile_name,
                                "status": (local.get("verdict") or {}).get("status"),
                                "parsed_ingredients": local.get("parsed_ingredients") or [],
                                "triggered": (local.get("verdict") or {}).get(
                                    "triggered_ingredients"
                                ),
                            }
                        )
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
                if exc.code >= 500:
                    n_5xx += 1
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
            if ps == "SAFE" and ls in _UNSAFE:
                unsafe_safe += 1
            entry = {
                "code": code,
                "profile": profile_name,
                "local_status": ls,
                "prod_status": ps,
                "agree": same,
                "hard_unsafe_safe": bool(ps == "SAFE" and ls in _UNSAFE),
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

    compared = agree["agree"] + agree["disagree"]
    agreement = (agree["agree"] / compared) if compared else 0.0
    hard_ok = unsafe_safe == 0 and n_5xx == 0
    agree_ok = (not args.same_seed) or agreement >= 0.95
    report = {
        "prod_base": args.prod_base,
        "api_key_sent": bool(args.api_key),
        "same_seed": args.same_seed,
        "reference_json": str(args.reference_json) if args.reference_json else None,
        "n_products_requested": len(products),
        "n_missing_text": missing,
        "n_errors": errors,
        "n_5xx": n_5xx,
        "hard_unsafe_safe": unsafe_safe,
        "hard_gates_pass": hard_ok,
        "agreement": round(agreement, 4),
        "agreement_gate_applied": args.same_seed,
        "agree": dict(agree),
        "diff_class": dict(diff_class),
        "note": (
            "95% agreement is only a gate with --same-seed against an ontology-seed "
            "reference. A local DB with bulk groups will disagree for data reasons."
        ),
        "rows": rows,
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n")
    if args.write_reference:
        args.write_reference.parent.mkdir(parents=True, exist_ok=True)
        args.write_reference.write_text(
            json.dumps(
                {
                    "same_seed": args.same_seed,
                    "n": len(reference_rows),
                    "rows": reference_rows,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("wrote reference", args.write_reference)
    print(json.dumps({k: report[k] for k in report if k != "rows"}, indent=2))
    print("out", _OUT)
    if not hard_ok:
        return 2
    if not agree_ok:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
