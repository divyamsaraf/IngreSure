"""Stress tests: 200+ ingredient labels with junk text; legacy vs IKE-2."""
from __future__ import annotations

import json

import pytest

from core.intent_detector import detect_intent
from tests.fixtures.labels.stress_label import (
    JUNK_BLOCKS,
    build_stress_label,
    run_stress_suite,
    run_user_input_stress,
)


@pytest.fixture(scope="module")
def stress_label() -> str:
    return build_stress_label(240)


def test_stress_label_has_200_plus_atoms(stress_label: str) -> None:
    from core.parsing.label_decomposer import decompose_label
    from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text

    cleaned = select_ingredient_label_text(fix_ocr_label_noise(stress_label))
    items = decompose_label(cleaned)
    assert len(items) >= 200, f"expected >=200 atoms, got {len(items)}"


def test_stress_suite_completes_without_error() -> None:
    report = run_stress_suite(ingredient_count=240, iterations=2, use_seeded_rules=True)
    assert report["decomposed_atoms"] >= 200
    assert len(report["profiles"]) == 6


def test_stress_no_false_safe_regressions_seeded_rules() -> None:
    """IKE-2 must not be SAFER than legacy on the mega-label (seeded rules)."""
    report = run_stress_suite(ingredient_count=240, iterations=1, use_seeded_rules=True)
    assert report["summary"]["false_safe_regressions"] == 0, json.dumps(
        report["false_safe_details"], indent=2
    )


def test_stress_junk_blocks_not_treated_as_full_ingredient_lists() -> None:
    """Standalone junk paragraphs should not yield hundreds of atoms."""
    from core.parsing.label_decomposer import decompose_label

    for block in JUNK_BLOCKS[:5]:
        items = decompose_label(block)
        assert len(items) < 15, f"junk block parsed too many atoms: {block[:60]!r} -> {len(items)}"


@pytest.mark.parametrize(
    "query",
    [
        "what's the weather today",
        "help",
        "???",
    ],
)
def test_junk_queries_not_ingredient_lists(query: str) -> None:
    result = detect_intent(query)
    assert result.intent in ("GENERAL_QUESTION", "GREETING", "PROFILE_UPDATE", "CLARIFICATION")
    assert len(result.ingredients) < 5


def test_user_input_stress_no_false_safe() -> None:
    report = run_user_input_stress(ingredient_count=240, use_seeded_rules=True)
    compared = [r for r in report["scenarios"] if r["verdict_match"] is not None]
    assert compared, "expected at least one compliance scenario"
    assert report["summary"]["false_safe_regressions"] == 0
    assert report["summary"]["verdict_match_rate"] == 1.0


def test_stress_latency_budget_seeded_rules() -> None:
    """Sanity ceiling — 220 atoms should finish in reasonable time on dev hardware."""
    report = run_stress_suite(ingredient_count=240, iterations=1, use_seeded_rules=True)
    assert report["latency"]["legacy_ms"]["p50"] < 120_000, "legacy too slow"
    assert report["latency"]["ike2_ms"]["p50"] < 120_000, "ike2 too slow"
