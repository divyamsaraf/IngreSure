"""CODEOWNERS + license attribution must stay the reviewed-PR gate."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.check_governance_protected_files import (
    PROTECTED,
    codeowners_covers_protected,
    main as check_main,
)

_REPO = Path(__file__).resolve().parents[3]
_ATTR = (
    _REPO
    / "backend"
    / "core"
    / "knowledge"
    / "ike2"
    / "etl"
    / "license_attribution.json"
)
_ALLOW = (
    _REPO
    / "backend"
    / "core"
    / "knowledge"
    / "ike2"
    / "etl"
    / "license_allowlist.json"
)


def test_codeowners_lists_allowlist_and_reviewed_negatives():
    assert codeowners_covers_protected() == []
    text = (_REPO / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "license_allowlist.json" in text
    assert "ike2_reviewed_negatives.json" in text
    assert "@divyamsaraf" in text


def test_protected_paths_exist():
    for rel in PROTECTED:
        assert (_REPO / rel).is_file(), rel


def test_governance_check_script_exits_0():
    assert check_main([]) == 0


def test_ogl_attribution_strings_exact():
    data = json.loads(_ATTR.read_text(encoding="utf-8"))
    assert data["owner_confirmed"] is False
    assert data["attributions"]["OGL-UK-3.0"] == (
        "Contains public sector information licensed under the Open Government Licence v3.0."
    )
    assert data["attributions"]["OGL-Canada-2.0"] == (
        "Contains information licensed under the Open Government Licence – Canada."
    )


def test_ogl_spdx_not_silently_in_allowlist():
    """Owner must confirm before OGL ids land on the allowlist (PR #17 / D10)."""
    allow = json.loads(_ALLOW.read_text(encoding="utf-8"))
    ids = set(allow.get("allowed_licenses") or [])
    assert "OGL-UK-3.0" not in ids
    assert "OGL-Canada-2.0" not in ids
