"""Phase 4 label corpus — parse quality + legacy/IKE-2 shadow gate (metric C)."""
from __future__ import annotations

import pytest

from tests.fixtures.labels.label_corpus_runner import (
    SHADOW_MATCH_THRESHOLD,
    assert_parse_quality,
    load_label_corpus,
    parse_label,
    run_shadow_report,
)

_CORPUS = load_label_corpus()
_CORPUS_IDS = [row["id"] for row in _CORPUS]


@pytest.mark.parametrize("row", _CORPUS, ids=_CORPUS_IDS)
def test_label_corpus_parse_quality(row: dict) -> None:
    items = parse_label(row)
    assert_parse_quality(row, items)


def test_label_corpus_has_at_least_200_rows() -> None:
    assert len(_CORPUS) >= 200, f"expected >=200 labels, got {len(_CORPUS)}"


def test_shadow_match_rate_at_least_85_percent() -> None:
    report = run_shadow_report()
    assert report["total"] > 0, "no shadow_check rows in corpus"
    assert report["match_rate"] >= SHADOW_MATCH_THRESHOLD, (
        f"shadow match {report['match_rate']:.1%} < {SHADOW_MATCH_THRESHOLD:.0%}; "
        f"mismatches={len(report['mismatches'])}"
    )


def test_zero_false_safe_shadow_regressions() -> None:
    report = run_shadow_report()
    false_safe = report["false_safe_regressions"]
    assert not false_safe, (
        f"{len(false_safe)} false-Safe regressions: "
        + ", ".join(f"{r['id']} ({r['legacy_verdict']}→{r['ike2_verdict']})" for r in false_safe[:5])
    )
