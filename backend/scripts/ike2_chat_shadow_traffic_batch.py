#!/usr/bin/env python3
"""Deliberate /chat/grocery traffic for Item 16 primary-window verification.

Mirrors ``ike2_api_shadow_traffic_batch.py`` but drives the real chat entry
point (intent detect → profile merge → parse → ``run_new_engine_chat``), so
``ike2_shadow_diffs`` land with ``source_route=chat``.

Examples::

    cd backend && python scripts/ike2_chat_shadow_traffic_batch.py --mode primary
    cd backend && python scripts/ike2_chat_shadow_traffic_batch.py --mode primary --limit 80
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

try:
    from dotenv import load_dotenv

    load_dotenv(_backend / ".env")
    load_dotenv(_repo / ".env")
except ImportError:
    pass

# Deliberate soak: no LLM latency, no chat throttle.
os.environ.setdefault("LLM_ENABLED", "false")
os.environ["RATE_LIMIT_CHAT_ANON"] = "100000/minute"
os.environ["RATE_LIMIT_CHAT_AUTH"] = "100000/minute"

CORPUS_PATH = _backend / "tests" / "fixtures" / "labels" / "corpus.jsonl"

# Same rotation as the API batch.
RESTRICTION_ROTATION = [
    ["vegan"],
    ["gluten_free"],
    ["celiac_strict"],
    ["peanut_allergy"],
    ["dairy_free"],
    ["egg_free"],
    ["hindu_vegetarian"],
    ["jain"],
    ["halal"],
    ["kosher"],
    ["vegetarian"],
    ["pescatarian"],
    ["vegan", "gluten_free"],
    ["hindu_vegetarian", "dairy_free"],
]

# Class-level fungal / fermentation coverage beyond the original yeast miss.
FERMENTATION_CASES = [
    ("yeast", ["jain"]),
    ("yeast extract", ["jain"]),
    ("tempeh", ["jain"]),
    ("baker's yeast", ["jain"]),
    ("nutritional yeast", ["jain"]),
    ("koji", ["jain"]),
    ("miso", ["jain"]),
    ("tamari", ["jain"]),
    ("natto", ["jain"]),
    ("mushroom", ["jain"]),
    ("yeast", ["vegan"]),
    ("tempeh", ["vegan"]),
    ("miso", ["vegetarian"]),
]


def _load_corpus(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _pick_restriction_ids(row: dict, index: int) -> list[str]:
    if row.get("restriction_ids"):
        return list(row["restriction_ids"])
    return list(RESTRICTION_ROTATION[index % len(RESTRICTION_ROTATION)])


def _profile_for_restriction_ids(rids: list[str]) -> dict[str, Any]:
    """Map engine restriction_ids → chat userProfile (diet / allergens / lifestyle).

    Chat cannot express every engine id 1:1 (e.g. ``celiac_strict``). Closest
    profile mapping is used; soak rows then show the *actual* ids chat derived.
    """
    diet = "No rules"
    allergens: list[str] = []
    lifestyle: list[str] = []

    for rid in rids:
        if rid == "vegan":
            diet = "Vegan"
        elif rid == "vegetarian":
            diet = "Vegetarian"
        elif rid == "pescatarian":
            diet = "Pescatarian"
        elif rid == "jain":
            diet = "Jain"
        elif rid == "halal":
            diet = "Halal"
        elif rid == "kosher":
            diet = "Kosher"
        elif rid == "hindu_vegetarian":
            diet = "Hindu Vegetarian"
        elif rid in ("gluten_free", "celiac_strict"):
            if "Gluten-Free" not in lifestyle:
                lifestyle.append("Gluten-Free")
        elif rid == "dairy_free":
            if "Dairy-Free" not in lifestyle:
                lifestyle.append("Dairy-Free")
        elif rid == "egg_free":
            if "Egg-Free" not in lifestyle:
                lifestyle.append("Egg-Free")
        elif rid == "peanut_allergy":
            if "Peanuts" not in allergens:
                allergens.append("Peanuts")
        else:
            # Unknown rid: leave as lifestyle token hope / skip
            pass

    return {
        "dietary_preference": diet,
        "allergens": allergens,
        "lifestyle": lifestyle,
    }


def _query_for_raw(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    low = text.lower()
    if low.startswith("ingredients:") or low.startswith("ingredient:"):
        return text
    return f"Ingredients: {text}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Item 16 chat-path traffic batch")
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--limit", type=int, default=0, help="Max corpus rows (0 = all)")
    parser.add_argument(
        "--mode",
        choices=("shadow", "primary"),
        default="primary",
        help="IKE2_MODE for this batch (default primary)",
    )
    parser.add_argument(
        "--skip-fermentation",
        action="store_true",
        help="Skip extra yeast/tempeh/koji/miso/… cases",
    )
    parser.add_argument(
        "--flush-seconds",
        type=float,
        default=5.0,
        help="Wait for background legacy-diff threads to flush (default 5)",
    )
    args = parser.parse_args(argv)

    os.environ["IKE2_MODE"] = args.mode
    os.environ["LLM_ENABLED"] = "false"

    from fastapi.testclient import TestClient

    from app import app

    client = TestClient(app)
    rows = _load_corpus(args.corpus)
    if args.limit > 0:
        rows = rows[: args.limit]

    ok = 0
    errors = 0
    fermentation_ok = 0
    batch_tag = uuid.uuid4().hex[:8]

    def _post(query: str, rids: list[str], *, label: str) -> None:
        nonlocal ok, errors, fermentation_ok
        profile = _profile_for_restriction_ids(rids)
        user_id = f"chat-batch-{batch_tag}-{ok + errors + fermentation_ok}"
        try:
            r = client.post(
                "/chat/grocery",
                json={
                    "query": query,
                    "user_id": user_id,
                    "userProfile": profile,
                },
            )
            if r.status_code != 200:
                errors += 1
                print(f"FAIL {label} status={r.status_code} {r.text[:200]}")
                return
            if "INGREDIENT_AUDIT" not in r.text and "Checking ingredients" not in r.text:
                errors += 1
                print(f"FAIL {label} no audit payload in response")
                return
            if label.startswith("ferm:"):
                fermentation_ok += 1
            else:
                ok += 1
        except Exception as exc:
            errors += 1
            print(f"EXC {label}: {exc}")

    for i, row in enumerate(rows):
        raw = (row.get("raw") or "").strip()
        if not raw:
            continue
        rids = _pick_restriction_ids(row, i)
        q = _query_for_raw(raw)
        _post(q, rids, label=f"corpus:{row.get('id', i)}")

    if not args.skip_fermentation:
        for name, rids in FERMENTATION_CASES:
            _post(_query_for_raw(name), list(rids), label=f"ferm:{name}")

    # Background legacy diffs are fire-and-forget.
    time.sleep(max(0.0, args.flush_seconds))

    print(
        json.dumps(
            {
                "corpus_rows": len(rows),
                "chat_corpus_ok": ok,
                "chat_fermentation_ok": fermentation_ok,
                "errors": errors,
                "ike2_mode": os.environ.get("IKE2_MODE"),
                "source_route": "chat",
                "batch_tag": batch_tag,
            },
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
