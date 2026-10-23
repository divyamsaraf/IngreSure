#!/usr/bin/env python3
"""Post-deploy smoke: /health fingerprint matches expected SHA; peanut is NOT_SAFE.

Usage::

    EXPECTED_GIT_SHA=$(git rev-parse HEAD) \\
      PROD_API_BASE=https://ingresure-api.gleeze.com \\
      PROD_API_KEY=... \\
      CORS_PREVIEW_ORIGIN=https://ingresure-xxxx.vercel.app \\
      python scripts/post_deploy_smoke.py

Exit 0 only when git_sha matches, peanut → NOT_SAFE, empty-profile 422,
oversize 413, and (when health.production) unauthenticated /api/v1 is 401.
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
_OVERSIZE = 512 * 1024 + 1


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


def _post(
    url: str,
    payload: dict | bytes,
    headers: dict,
    *,
    extra_headers: dict | None = None,
) -> tuple[int, dict | str]:
    if isinstance(payload, bytes):
        data = payload
    else:
        data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **headers, **(extra_headers or {})}
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


def _options(url: str, origin: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        method="OPTIONS",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL) as resp:
            return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers)


def main() -> int:
    base = (os.environ.get("PROD_API_BASE") or _DEFAULT_BASE).rstrip("/")
    expected = (os.environ.get("EXPECTED_GIT_SHA") or "").strip()
    api_key = (os.environ.get("PROD_API_KEY") or "").strip()
    preview = (os.environ.get("CORS_PREVIEW_ORIGIN") or "").strip()
    headers = {"X-API-Key": api_key} if api_key else {}

    failures: list[str] = []
    production = False

    code, health = _get(f"{base}/health")
    if code != 200 or not isinstance(health, dict):
        failures.append(f"/health → {code} {health!r}")
    else:
        sha = health.get("git_sha") or ""
        production = bool(health.get("production"))
        print(json.dumps({k: health.get(k) for k in (
            "git_sha",
            "ike2_schema_version",
            "engine",
            "environment",
            "production",
            "ike2_live_audit",
        )}, indent=2))
        if expected and sha != expected and not (
            len(expected) >= 7 and sha.startswith(expected[:7])
        ):
            failures.append(
                f"git_sha mismatch: running={sha!r} expected={expected!r}"
            )
        if health.get("engine") != "ike2":
            failures.append(f"engine={health.get('engine')!r} (want ike2)")
        if "ike2_live_audit" not in health:
            failures.append("health missing ike2_live_audit")

    eval_url = f"{base}/api/v1/evaluate-product"
    code, body = _post(
        eval_url,
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
        if any(
            isinstance(a, str) and a.replace("%", "").replace(".", "").isdigit()
            for a in parsed
        ):
            failures.append(f"parser left percent artifact in {parsed!r}")

    code, body = _post(
        eval_url,
        {"ingredients_text": "water"},
        headers,
    )
    if code != 422:
        failures.append(f"empty restriction_ids → {code} (want 422) {body!r}")

    oversize = (
        b'{"ingredients_text":"' + (b"a" * _OVERSIZE) + b'","restriction_ids":["vegan"]}'
    )
    code, body = _post(eval_url, oversize, headers)
    if code != 413:
        failures.append(f"oversize body → {code} (want 413) {body!r}")

    if production:
        code, body = _post(
            eval_url,
            {
                "ingredients_text": "water",
                "restriction_ids": ["vegan"],
            },
            {},
        )
        if code != 401:
            failures.append(
                f"no API key on production → {code} (want 401) {body!r}"
            )

    if preview:
        code, hdrs = _options(eval_url, preview)
        allow = (hdrs.get("Access-Control-Allow-Origin") or "").lower()
        if code not in (200, 204) or allow not in (preview.lower(), "*"):
            failures.append(
                f"CORS preview {preview!r} → {code} allow={allow!r}"
            )

    if failures:
        print("FAIL:", *failures, sep="\n  ")
        return 1
    print("OK: fingerprint + peanut NOT_SAFE + 422/413" + (" + 401" if production else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
