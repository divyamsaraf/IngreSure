#!/usr/bin/env python3
"""Run Step 1 corpus (tests/corpus/input_cases.jsonl) against current local code.

Classifies each case as: crash_500, silent_drop, wrong_intent, wrong_restriction,
unsafe_SAFE, or ok. Prints a failure matrix by area (A–E).
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_API_V1_DEFAULT", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_ANON", "100000/minute")
os.environ.setdefault("RATE_LIMIT_CHAT_AUTH", "100000/minute")

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from core.intent_detector import detect_intent  # noqa: E402
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings  # noqa: E402
from core.stream_tags import INGREDIENT_AUDIT_TAG, PROFILE_UPDATE_TAG  # noqa: E402

_CORPUS = _BACKEND / "tests" / "corpus" / "input_cases_expanded.jsonl"
_OUT = _BACKEND / ".local_reports" / "step1_spec_matrix.json"

_RID_HINTS = (
    ("peanut", "peanut_allergy"),
    ("gluten", "gluten_free"),
    ("dairy", "dairy_free"),
    ("vegan", "vegan"),
    ("jain", "jain"),
    ("halal", "halal"),
    ("celiac", "gluten_free"),
)

_PROFILE_FOR_RID = {
    "peanut_allergy": {"dietary_preference": "No rules", "allergens": ["peanuts"], "lifestyle": []},
    "gluten_free": {"dietary_preference": "Gluten-Free", "allergens": [], "lifestyle": []},
    "dairy_free": {"dietary_preference": "Dairy-Free", "allergens": ["milk"], "lifestyle": []},
    "vegan": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
    "jain": {"dietary_preference": "Jain", "allergens": [], "lifestyle": []},
    "halal": {"dietary_preference": "Halal", "allergens": [], "lifestyle": []},
}


def _rids(case: dict) -> list[str]:
    if case.get("restriction_ids"):
        return list(case["restriction_ids"])
    mn = (case.get("must_never") or "").lower()
    out: list[str] = []
    for needle, rid in _RID_HINTS:
        if needle in mn and rid not in out:
            out.append(rid)
    return out


def _profile(rids: list[str]) -> dict:
    merged = {"dietary_preference": "No rules", "allergens": [], "lifestyle": []}
    for rid in rids:
        p = _PROFILE_FOR_RID.get(rid)
        if not p:
            continue
        if p["dietary_preference"] != "No rules":
            merged["dietary_preference"] = p["dietary_preference"]
        for a in p["allergens"]:
            if a not in merged["allergens"]:
                merged["allergens"].append(a)
        for ls in p["lifestyle"]:
            if ls not in merged["lifestyle"]:
                merged["lifestyle"].append(ls)
    return merged


def _extract_audit(body: str):
    start = body.find(INGREDIENT_AUDIT_TAG)
    if start == -1:
        return None
    end = body.find(INGREDIENT_AUDIT_TAG, start + len(INGREDIENT_AUDIT_TAG))
    if end == -1:
        return None
    raw = body[start + len(INGREDIENT_AUDIT_TAG) : end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _verdict_status(payload) -> str | None:
    if not payload:
        return None
    if isinstance(payload, dict):
        if "verdict" in payload and isinstance(payload["verdict"], dict):
            return payload["verdict"].get("status")
        groups = payload.get("groups") or []
        if groups:
            # worst of audit groups
            order = {"NOT_SAFE": 3, "AVOID": 3, "UNCERTAIN": 2, "CHECK": 2, "SAFE": 1}
            worst = "SAFE"
            for g in groups:
                st = str(g.get("status") or "").upper()
                if order.get(st, 0) > order.get(worst, 0):
                    worst = "NOT_SAFE" if st in ("AVOID", "NOT_SAFE") else st
            return worst
    return None


def _expected_tokens(text: str) -> list[str]:
    needles = [
        "sugar",
        "water",
        "salt",
        "peanut",
        "wheat",
        "soy",
        "milk",
        "cocoa",
        "oat",
        "atta",
        "maida",
        "ghee",
        "dahi",
        "weizen",
        "milch",
        "blé",
        "lait",
        "caseinate",
        "parmesan",
        "onion",
        "gelatin",
        "xylitol",
    ]
    low = (text or "").lower()
    return [n for n in needles if n in low]


def _silent_drop(raw: str, parsed: list[str]) -> bool:
    blob = " ".join(parsed or []).lower()
    missed = [t for t in _expected_tokens(raw) if t not in blob]
    return bool(missed) and bool(parsed is not None)


def _classify(case: dict, *, status_code: int | None, body, parsed, intent, exception) -> list[str]:
    fails: list[str] = []
    mn = (case.get("must_never") or "").lower()
    expected = (case.get("expected") or "").lower()
    if exception or status_code == 500:
        fails.append("crash_500")
    if "crash" in mn and (exception or status_code == 500):
        fails.append("crash_500")
    if status_code and status_code >= 500:
        fails.append("crash_500")

    if parsed is not None and _silent_drop(case.get("input") or "", parsed):
        if "drop" in mn or "silent" in mn or case["area"] == "A":
            fails.append("silent_drop")

    if case["route"] == "chat" and intent:
        # wrong intent: greeting treated as ingredient SAFE, or recipe as packaged SAFE
        if "greeting" in expected and intent.intent not in ("GREETING", "GENERAL_QUESTION"):
            fails.append("wrong_intent")
        if "ask" in expected and intent.intent == "INGREDIENT_QUERY" and not intent.ingredients:
            pass
        if "emergency" in expected and intent.intent not in ("GENERAL_QUESTION", "GREETING"):
            # evaluating ingredients during emergency is wrong intent
            if intent.has_ingredients:
                fails.append("wrong_intent")

    if "restriction" in mn or "silent vegan" in mn or "confirm" in expected:
        if intent and intent.has_profile_update:
            pu = intent.profile_updates or {}
            if "do not apply vegan" in expected or "negation does not add vegan" in expected:
                if str(pu.get("dietary_preference") or "").lower() == "vegan":
                    fails.append("wrong_restriction")
            if "confirm before removing" in expected or "do not apply vegan without confirm" in expected:
                if pu.get("dietary_preference") or pu.get("remove_allergens"):
                    fails.append("wrong_restriction")
        if "unsupported" in expected and intent and not intent.has_profile_update:
            # keto/diabetic silently ignored
            fails.append("wrong_restriction")

    verdict = _verdict_status(body if isinstance(body, dict) else None)
    if isinstance(body, str):
        audit = _extract_audit(body)
        verdict = _verdict_status(audit) or verdict
        if "safe" in body.lower() and "not_safe" not in (verdict or "").lower():
            if "SAFE" in (case.get("must_never") or "") or "firm SAFE" in mn:
                if verdict == "SAFE":
                    fails.append("unsafe_SAFE")
    if verdict == "SAFE" and ("safe" in mn or "SAFE" in (case.get("must_never") or "")):
        fails.append("unsafe_SAFE")

    # 400/422 expected for contradiction / validation
    if "400" in expected or "422" in expected or "413" in expected:
        if status_code not in (400, 413, 422):
            if status_code == 200 and verdict == "SAFE":
                fails.append("unsafe_SAFE")
            elif status_code == 200:
                fails.append("wrong_restriction")
            elif status_code and status_code >= 500:
                fails.append("crash_500")

    # HTTP 500 must never
    if "http 500" in mn and status_code == 500:
        fails.append("crash_500")

    return sorted(set(fails))


def _run_case(client: TestClient, case: dict) -> dict:
    route = case["route"]
    raw_input = case["input"]
    rids = _rids(case)
    parsed = None
    intent = None
    status_code = None
    body = None
    exception = None
    try:
        if raw_input == "OVERSIZE":
            raw_input = "water, salt, " + ("x" * (600 * 1024))
        if route == "evaluate-product":
            r = client.post(
                "/api/v1/evaluate-product",
                json={"ingredients_text": raw_input, "restriction_ids": rids},
            )
            status_code = r.status_code
            try:
                body = r.json()
            except Exception:
                body = r.text
            if isinstance(body, dict):
                parsed = body.get("parsed_ingredients")
            if parsed is None and isinstance(raw_input, str) and raw_input != "OVERSIZE":
                parsed = preprocess_ingredients_to_strings(raw_input)
        elif route == "evaluate-compliance":
            if case.get("raw"):
                payload = {"ingredients": raw_input, "restriction_ids": rids}
            elif isinstance(raw_input, str) and raw_input.lstrip().startswith("{"):
                payload = json.loads(raw_input)
            elif isinstance(raw_input, list):
                payload = {"ingredients": raw_input, "restriction_ids": rids}
            else:
                payload = {
                    "ingredients": [raw_input],
                    "restriction_ids": rids,
                }
            r = client.post("/api/v1/evaluate-compliance", json=payload)
            status_code = r.status_code
            try:
                body = r.json()
            except Exception:
                body = r.text
        elif route == "profile":
            payload = json.loads(raw_input)
            r = client.post("/profile", json=payload)
            status_code = r.status_code
            try:
                body = r.json()
            except Exception:
                body = r.text
        elif route == "chat":
            intent = detect_intent(raw_input if isinstance(raw_input, str) else str(raw_input))
            spec = case.get("spec_id") or case.get("id")
            variant = case.get("variant", 1)
            r = client.post(
                "/chat/grocery",
                json={
                    "query": raw_input,
                    "user_id": f"step1-{spec}-{variant}",
                    "userProfile": _profile(rids),
                },
            )
            status_code = r.status_code
            body = r.text
            parsed = list(intent.ingredients) if intent else []
        else:
            raise ValueError(f"unknown route {route}")
    except Exception as e:  # noqa: BLE001
        exception = f"{type(e).__name__}: {e}"
        status_code = status_code or 500
        traceback.print_exc()

    fails = _classify(
        case,
        status_code=status_code,
        body=body,
        parsed=parsed,
        intent=intent,
        exception=exception,
    )
    spec_id = case.get("spec_id") or case.get("id")
    return {
        "id": spec_id,
        "spec_id": spec_id,
        "variant": case.get("variant"),
        "area": case["area"],
        "route": route,
        "status_code": status_code,
        "intent": getattr(intent, "intent", None),
        "profile_updates": getattr(intent, "profile_updates", None) if intent else None,
        "parsed": (parsed or [])[:20] if parsed is not None else None,
        "verdict": _verdict_status(body if isinstance(body, dict) else None)
        or _verdict_status(_extract_audit(body) if isinstance(body, str) else None),
        "exception": exception,
        "fails": fails,
    }


def main() -> int:
    cases = [json.loads(line) for line in _CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    client = TestClient(app, raise_server_exceptions=False)
    rows = []
    matrix = defaultdict(lambda: defaultdict(int))
    for case in cases:
        row = _run_case(client, case)
        rows.append(row)
        if row["fails"]:
            for f in row["fails"]:
                matrix[case["area"]][f] += 1
        else:
            matrix[case["area"]]["ok"] += 1
        mark = ",".join(row["fails"]) if row["fails"] else "ok"
        print(
            f"{row['spec_id']:4} v{row.get('variant') or '-'} {mark:22} "
            f"http={row['status_code']} intent={row['intent']} verdict={row['verdict']}"
        )

    summary = {area: dict(counts) for area, counts in sorted(matrix.items())}
    by_spec: dict[str, dict] = {}
    for row in rows:
        sid = row["spec_id"]
        rec = by_spec.setdefault(sid, {"ok": 0, "fail": 0, "fails": []})
        if row["fails"]:
            rec["fail"] += 1
            rec["fails"].extend(row["fails"])
        else:
            rec["ok"] += 1
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(
        json.dumps({"summary": summary, "by_spec": by_spec, "rows": rows}, indent=2) + "\n"
    )
    print("\n=== failure matrix by area ===")
    print(json.dumps(summary, indent=2))
    print("\n=== by spec ID ===")
    for sid, rec in sorted(by_spec.items()):
        mark = "ok" if rec["fail"] == 0 else ",".join(sorted(set(rec["fails"])))
        print(f"{sid:4} ok={rec['ok']} fail={rec['fail']} {mark}")
    n_fail = sum(1 for r in rows if r["fails"])
    n_spec_fail = sum(1 for rec in by_spec.values() if rec["fail"])
    print(
        f"\n{n_fail}/{len(rows)} variants failed; "
        f"{n_spec_fail}/{len(by_spec)} spec IDs have a failing variant. wrote {_OUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
