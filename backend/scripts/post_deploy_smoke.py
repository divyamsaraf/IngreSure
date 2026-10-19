#!/usr/bin/env python3
"""Post-deploy smoke: /health fingerprint matches expected SHA; peanut is NOT_SAFE.

Usage::

    EXPECTED_GIT_SHA=$(git rev-parse HEAD) \\
      PROD_API_BASE=https://ingresure-api.gleeze.com \\
      PROD_API_KEY=... \\
      python scripts/post_deploy_smoke.py

Exit 0 only when git_sha matches and PEANUTS (49.5%) → NOT_SAFE for peanut_allergy.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

try:
    import certifi

    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _SSL = ssl.create_default_context()

_DEFAULT_BASE = "https://ingresure-api.gleeze.com"


def _get(url: str, headers: dict | None = None) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:500]
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body


def _post(url: str, payload: dict, headers: dict) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:500]
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body


def main() -> int:
    base = (os.environ.get("PROD_API_BASE") or _DEFAULT_BASE).rstrip("/")
    expected = (os.environ.get("EXPECTED_GIT_SHA") or "").strip()
    api_key = (os.environ.get("PROD_API_KEY") or "").strip()
    headers = {"X-API-Key": api_key} if api_key else {}

    failures: list[str] = []

    code, health = _get(f"{base}/health")
    if code != 200 or not isinstance(health, dict):
        failures.append(f"/health → {code} {health!r}")
    else:
        sha = health.get("git_sha") or ""
        print(json.dumps({k: health.get(k) for k in (
            "git_sha", "ike2_schema_version", "engine", "environment", "production"
        )}, indent=2))
        if expected and sha != expected and not (
            len(expected) >= 7 and sha.startswith(expected[:7])
        ):
            failures.append(
                f"git_sha mismatch: running={sha!r} expected={expected!r}"
            )
        if health.get("engine") not in ("ike2", None):
            # None = pre-fingerprint deploy
            if health.get("engine") != "ike2":
                failures.append(f"engine={health.get('engine')!r} (want ike2)")

    code, body = _post(
        f"{base}/api/v1/evaluate-product",
        {
            "ingredients_text": "PEANUTS (49.5%), honey, salt",
            "restriction_ids": ["peanut_allergy"],
        },
        headers,
    )
    if code == 401:
        failures.append(
            "/api/v1/evaluate-product → 401 (set PROD_API_KEY for keyed smoke)"
        )
    elif code != 200 or not isinstance(body, dict):
        failures.append(f"peanut evaluate → {code} {body!r}")
    else:
        status = (body.get("verdict") or {}).get("status")
        parsed = body.get("parsed_ingredients") or []
        print("peanut_status", status, "parsed", parsed)
        if status != "NOT_SAFE":
            failures.append(f"peanut status={status!r} (want NOT_SAFE)")
        # Composition-% must not leave a bare percent atom on current main.
        if any(
            isinstance(a, str) and a.replace("%", "").replace(".", "").isdigit()
            for a in parsed
        ):
            failures.append(f"parser left percent artifact in {parsed!r}")

    if failures:
        print("FAIL:", *failures, sep="\n  ")
        return 1
    print("OK: fingerprint + peanut NOT_SAFE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
