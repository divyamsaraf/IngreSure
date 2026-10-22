"""Verdict LLM prose is built from structured evidence and must match status."""
from core.llm_response import _explanation_contradicts_status
from core.models.verdict import VerdictStatus


def test_safe_prose_cannot_say_not_safe():
    assert _explanation_contradicts_status("This is not safe.", VerdictStatus.SAFE)


def test_not_safe_prose_cannot_say_safe_to_eat():
    assert _explanation_contradicts_status("This is safe to eat.", VerdictStatus.NOT_SAFE)


def test_matching_prose_ok():
    assert not _explanation_contradicts_status(
        "No disqualifying ingredients were found on this label.",
        VerdictStatus.SAFE,
    )
