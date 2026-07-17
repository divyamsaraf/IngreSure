"""Helpers for the Phase 4 label corpus (parse + legacy/IKE-2 shadow comparison)."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from core.knowledge.ike2.shadow.comparator import compare
from core.knowledge.ike2.shadow.runner import ike2_external_verdict
from core.parsing.label_decomposer import decompose_label

CORPUS_PATH = pathlib.Path(__file__).parent / "corpus.jsonl"
SHADOW_MATCH_THRESHOLD = 0.85


def load_label_corpus(path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    corpus_path = path or CORPUS_PATH
    rows: list[dict[str, Any]] = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def legacy_external_verdict(raw: str, restriction_ids: list[str]) -> str:
    from core.bridge import run_new_engine_chat

    verdict = run_new_engine_chat(
        [raw],
        restriction_ids=restriction_ids,
        use_api_fallback=False,
    )
    return verdict.status.value


def shadow_compare_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row["raw"]
    restriction_ids = row.get("restriction_ids") or []
    legacy = legacy_external_verdict(raw, restriction_ids)
    ike2 = ike2_external_verdict([raw], restriction_ids, None)
    return compare(legacy, ike2, raw)


def parse_label(row: dict[str, Any]) -> list:
    return decompose_label(row["raw"])


def assert_parse_quality(row: dict[str, Any], items: list) -> None:
    names = [i.name for i in items]
    label_id = row.get("id", "?")

    if row.get("must_not_include_brackets"):
        assert not any("[" in n or "]" in n for n in names), f"{label_id}: brackets in {names}"

    if row.get("must_not_include_prefix"):
        assert not any(n.startswith("ingredients") for n in names), names

    for token in row.get("must_not_include", []):
        assert not any(token in n for n in names), f"{label_id}: unwanted {token!r} in {names}"

    for token in row.get("must_include", []):
        assert any(token in n for n in names), f"{label_id}: missing {token!r} in {names}"

    min_atoms = row.get("min_atoms")
    max_atoms = row.get("max_atoms")
    if min_atoms is not None:
        assert len(names) >= min_atoms, f"{label_id}: expected >={min_atoms} atoms, got {len(names)}"
    if max_atoms is not None:
        assert len(names) <= max_atoms, f"{label_id}: expected <={max_atoms} atoms, got {len(names)}"

    by_trace = {i.name: i.trace for i in items}
    for atom in row.get("trace_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{label_id}: trace atom {atom!r} missing"
        assert by_trace.get(match) is True, f"{label_id}: {match} should be trace"

    by_may_contain = {i.name: i.may_contain for i in items}
    for atom in row.get("may_contain_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{label_id}: may_contain atom {atom!r} missing"
        assert by_may_contain.get(match) is True, f"{label_id}: {match} should be may_contain"


def run_shadow_report(
    rows: list[dict[str, Any]] | None = None,
    *,
    threshold: float = SHADOW_MATCH_THRESHOLD,
) -> dict[str, Any]:
    corpus = rows if rows is not None else load_label_corpus()
    shadow_rows = [r for r in corpus if r.get("shadow_check")]
    if not shadow_rows:
        return {
            "total": 0,
            "matches": 0,
            "match_rate": 1.0,
            "false_safe_regressions": [],
            "mismatches": [],
            "threshold": threshold,
            "passed": True,
        }

    matches = 0
    mismatches: list[dict[str, Any]] = []
    false_safe: list[dict[str, Any]] = []

    for row in shadow_rows:
        diff = shadow_compare_row(row)
        if diff["match"]:
            matches += 1
        else:
            mismatches.append({**diff, "id": row.get("id")})
        if diff["false_safe_regression"]:
            false_safe.append({**diff, "id": row.get("id")})

    match_rate = matches / len(shadow_rows)
    return {
        "total": len(shadow_rows),
        "matches": matches,
        "match_rate": match_rate,
        "false_safe_regressions": false_safe,
        "mismatches": mismatches,
        "threshold": threshold,
        "passed": match_rate >= threshold and not false_safe,
    }
