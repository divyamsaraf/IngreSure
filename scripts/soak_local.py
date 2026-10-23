#!/usr/bin/env python3
"""Capped local soak stub: GET /health plus a few evaluate-product calls.

Not run in CI by default. Hits a local server (127.0.0.1) or ``--in-process``
TestClient. Never uses production URLs.

  python scripts/soak_local.py --cap 8
  python scripts/soak_local.py --in-process --cap 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CAP = 8
DEFAULT_BASE = "http://127.0.0.1:8000"
_REPO = Path(__file__).resolve().parent.parent
_BACKEND = _REPO / "backend"
_DEFAULT_OUT = _BACKEND / ".local_reports" / "soak_local.json"
_PAYLOADS = (
    {"ingredients_text": "water, salt", "restriction_ids": ["vegan"]},
    {"ingredients_text": "peanuts, salt", "restriction_ids": ["peanut_allergy"]},
    {"ingredients_text": "milk, sugar", "restriction_ids": ["dairy_free"]},
)


def _http_get_json(url: str, timeout: float = 2.0) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, body: dict, timeout: float = 10.0) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"text": raw[:300]}
        return int(exc.code), parsed


def _assert_local_base(base: str) -> None:
    lowered = (base or "").lower()
    if "127.0.0.1" not in lowered and "localhost" not in lowered:
        raise ValueError(f"refusing non-local soak URL: {base}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--in-process", action="store_true")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(argv)
    cap = max(1, int(args.cap))
    n500 = 0
    health_ok = False
    evaluate_n = 0

    try:
        if args.in_process:
            os.environ.setdefault("LLM_ENABLED", "false")
            os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")
            sys.path.insert(0, str(_BACKEND))
            from fastapi.testclient import TestClient

            from app import app

            client = TestClient(app, raise_server_exceptions=False)
            health = client.get("/health")
            health_ok = health.status_code == 200
            for i in range(cap):
                body = _PAYLOADS[i % len(_PAYLOADS)]
                resp = client.post("/api/v1/evaluate-product", json=body)
                evaluate_n += 1
                if resp.status_code == 500:
                    n500 += 1
        else:
            _assert_local_base(args.base_url)
            health = _http_get_json(args.base_url.rstrip("/") + "/health")
            health_ok = bool(health)
            for i in range(cap):
                body = _PAYLOADS[i % len(_PAYLOADS)]
                code, _payload = _http_post_json(
                    args.base_url.rstrip("/") + "/api/v1/evaluate-product",
                    body,
                )
                evaluate_n += 1
                if code == 500:
                    n500 += 1
    except Exception as exc:
        report = {
            "health_ok": False,
            "evaluate_n": evaluate_n,
            "http_500": n500,
            "cap": cap,
            "error": str(exc),
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

    report = {
        "health_ok": health_ok,
        "evaluate_n": evaluate_n,
        "http_500": n500,
        "cap": cap,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not health_ok or n500:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
