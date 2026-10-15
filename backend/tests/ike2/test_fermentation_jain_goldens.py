"""Item 2 Prompt 7: Jain fermentation-class goldens.

Never firm SAFE for koji / miso / tamari / natto / yeast / tempeh (and the
compound forms that historically collapsed to compositional keywords only).
UNCERTAIN / WARN→external UNCERTAIN is acceptable where unresolved or
fermented-only (Item 3.1 P2 backlog owns firm Avoid anchors for miso-class).

Do not weaken the comparator to hide NOT_SAFE→SAFE.
"""
from __future__ import annotations

import pytest

from core.bridge import _run_ike2_compliance, map_ike2_to_compliance_verdict
from core.compound_expansion import expand_compounds
from tests.ike2.golden_runner import run_case

# Bare process foods named in Prompt 7.
_BARE = (
    "koji",
    "miso",
    "tamari",
    "natto",
    "yeast",
    "tempeh",
    "yeast extract",
)

# Prefixed forms that Prompt 1 found collapsing to soy/wheat alone (false SAFE).
_COMPOUNDS = (
    "soy tempeh",
    "organic soy tempeh",
    "soy miso",
    "barley miso",
    "wheat koji",
    "soy natto",
)

_PROCESS_TOKENS = {
    "soy tempeh": "tempeh",
    "organic soy tempeh": "tempeh",
    "soy miso": "miso",
    "barley miso": "miso",
    "wheat koji": "koji",
    "soy natto": "natto",
}


def _jain_never_safe(label: str) -> str:
    result, inputs, display = _run_ike2_compliance([label], ["jain"])
    verdict = map_ike2_to_compliance_verdict(result, inputs, input_display_map=display)
    return verdict.status.value


@pytest.mark.parametrize("label", _BARE)
def test_jain_bare_fermentation_never_firm_safe_bridge(label: str):
    assert _jain_never_safe(label) != "SAFE", label


@pytest.mark.parametrize("label", _COMPOUNDS)
def test_jain_compound_fermentation_never_firm_safe_bridge(label: str):
    assert _jain_never_safe(label) != "SAFE", label


@pytest.mark.parametrize("label,token", list(_PROCESS_TOKENS.items()))
def test_compound_retains_process_token(label: str, token: str):
    expanded, _, _ = expand_compounds([label], role_index={})
    assert token in expanded, (label, expanded)


@pytest.mark.parametrize(
    "label",
    _BARE
    + (
        "soy tempeh",
        "soy miso",
        "wheat koji",
        "soy natto",
    ),
)
def test_jain_fermentation_never_safe_via_golden_runner(label: str):
    """Same gate as must_never_be_safe corpus (parse_atoms → resolve → evaluate)."""
    case = {
        "raw_input": label,
        "profile": {"restrictions": {"jain": "preference"}},
        "region": None,
    }
    assert run_case(case) != "SAFE", label


def test_tempeh_and_yeast_remain_not_safe_not_merely_uncertain():
    """Anchored fungal canons stay firm Avoid — do not soften to hide regressions."""
    for label in ("tempeh", "yeast", "yeast extract", "soy tempeh"):
        status = _jain_never_safe(label)
        assert status == "NOT_SAFE", (label, status)
