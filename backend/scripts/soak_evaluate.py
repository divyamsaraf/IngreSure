#!/usr/bin/env python3
"""Soak: 648 evaluate-product requests, serial vs 16 workers. Verdicts must match; no 500."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_ANON", "100000/minute")

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

N = 648
WORKERS = 16

_PAYLOADS = [
    ("water, salt, sugar", ["vegan"]),
    ("milk, sugar", ["dairy_free"]),
    ("peanuts, salt", ["peanut_allergy"]),
    ("wheat flour, water", ["gluten_free"]),
    ("oats, salt", ["vegan"]),
    ("gelatin, sugar", ["halal"]),
    ("atta, maida, ghee", ["gluten_free"]),
    ("flavouring (contains milk)", ["dairy_free"]),
    ("E330, sugar", ["vegan"]),
    ("soy lecithin, water", ["soy_allergy"]),
    ("palm oil or sunflower oil", ["vegan"]),
    ("chocolate (sugar, cocoa butter, milk), flour", ["dairy_free"]),
]


def _bodies() -> list[dict]:
    out = []
    for i in range(N):
        text, rids = _PAYLOADS[i % len(_PAYLOADS)]
        out.append({"ingredients_text": text, "restriction_ids": rids, "_i": i})
    return out


def _one(client: TestClient, body: dict) -> tuple[int, int, str]:
    payload = {k: v for k, v in body.items() if k != "_i"}
    r = client.post("/api/v1/evaluate-product", json=payload)
    status = "ERR"
    if r.status_code == 200:
        try:
            status = r.json()["verdict"]["status"]
        except Exception:
            status = "PARSE"
    return body["_i"], r.status_code, status


def main() -> int:
    client = TestClient(app, raise_server_exceptions=False)
    bodies = _bodies()
    serial = [_one(client, b) for b in bodies]
    parallel = [None] * N
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_one, client, b) for b in bodies]
        for fut in as_completed(futs):
            i, code, status = fut.result()
            parallel[i] = (i, code, status)
    n500 = sum(1 for _, code, _ in serial + [p for p in parallel if p] if code == 500)
    mismatch = [
        (s, p)
        for s, p in zip(serial, parallel)
        if p is None or s[1] != p[1] or s[2] != p[2]
    ]
    report = {
        "n": N,
        "workers": WORKERS,
        "http_500": n500,
        "mismatch": len(mismatch),
        "serial_codes": sorted({c for _, c, _ in serial}),
        "sample_mismatch": mismatch[:10],
    }
    out = _BACKEND / ".local_reports" / "soak_648.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if n500 or mismatch:
        print("SOAK FAIL")
        return 1
    print("SOAK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
