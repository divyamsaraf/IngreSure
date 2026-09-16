"""IKE2_MODE config and /api/v1 evaluate routing (Item 16)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.models.verdict import ComplianceVerdict, VerdictStatus


def test_get_ike2_mode_defaults_to_shadow(monkeypatch):
    monkeypatch.delenv("IKE2_MODE", raising=False)
    from core.config import get_ike2_mode

    assert get_ike2_mode() == "shadow"


@pytest.mark.parametrize("mode", ["legacy", "shadow", "primary"])
def test_get_ike2_mode_accepts_valid_values(monkeypatch, mode):
    monkeypatch.setenv("IKE2_MODE", mode)
    from core.config import get_ike2_mode

    assert get_ike2_mode() == mode


def test_get_ike2_mode_invalid_falls_back_to_shadow(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "bogus")
    from core.config import get_ike2_mode

    assert get_ike2_mode() == "shadow"


def test_get_ike2_mode_case_insensitive(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "PRIMARY")
    from core.config import get_ike2_mode

    assert get_ike2_mode() == "primary"


def _verdict(status: str) -> ComplianceVerdict:
    return ComplianceVerdict(status=VerdictStatus(status))


def test_evaluate_mode_legacy_serves_legacy_only(monkeypatch):
    from core.api import v1_evaluate as mod

    legacy_v = _verdict("NOT_SAFE")
    ike2_v = _verdict("SAFE")
    legacy_fn = MagicMock(return_value=legacy_v)
    ike2_fn = MagicMock(return_value=(ike2_v, []))
    shadow_fn = MagicMock()
    schedule_fn = MagicMock()
    monkeypatch.setattr(mod, "get_ike2_mode", lambda: "legacy")
    monkeypatch.setattr(mod, "_run_legacy_evaluate", legacy_fn)
    monkeypatch.setattr(mod, "_run_ike2_evaluate_with_flags", ike2_fn)
    monkeypatch.setattr(mod, "_log_shadow_diff", shadow_fn)
    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", schedule_fn)

    out = mod.evaluate_ingredients(["gelatin"], ["vegan"])
    assert out is legacy_v
    legacy_fn.assert_called_once()
    ike2_fn.assert_not_called()
    shadow_fn.assert_not_called()
    schedule_fn.assert_not_called()


def test_evaluate_mode_shadow_serves_legacy_and_logs_diff(monkeypatch):
    from core.api import v1_evaluate as mod

    legacy_v = _verdict("NOT_SAFE")
    ike2_v = _verdict("SAFE")
    legacy_fn = MagicMock(return_value=legacy_v)
    ike2_fn = MagicMock(return_value=(ike2_v, [{"animal_origin": True}]))
    shadow_fn = MagicMock()
    schedule_fn = MagicMock()
    monkeypatch.setattr(mod, "get_ike2_mode", lambda: "shadow")
    monkeypatch.setattr(mod, "_run_legacy_evaluate", legacy_fn)
    monkeypatch.setattr(mod, "_run_ike2_evaluate_with_flags", ike2_fn)
    monkeypatch.setattr(mod, "_log_shadow_diff", shadow_fn)
    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", schedule_fn)

    out = mod.evaluate_ingredients(["gelatin"], ["vegan"])
    assert out is legacy_v
    legacy_fn.assert_called_once()
    ike2_fn.assert_called_once()
    shadow_fn.assert_called_once()
    schedule_fn.assert_not_called()
    call_kw = shadow_fn.call_args
    assert call_kw[0][0] == "NOT_SAFE"
    assert call_kw[0][1] == "SAFE"


def test_evaluate_mode_primary_serves_ike2_and_schedules_legacy_diff(monkeypatch):
    from core.api import v1_evaluate as mod

    legacy_v = _verdict("NOT_SAFE")
    ike2_v = _verdict("SAFE")
    legacy_fn = MagicMock(return_value=legacy_v)
    ike2_fn = MagicMock(return_value=(ike2_v, []))
    shadow_fn = MagicMock()
    schedule_fn = MagicMock()
    monkeypatch.setattr(mod, "get_ike2_mode", lambda: "primary")
    monkeypatch.setattr(mod, "_run_legacy_evaluate", legacy_fn)
    monkeypatch.setattr(mod, "_run_ike2_evaluate_with_flags", ike2_fn)
    monkeypatch.setattr(mod, "_log_shadow_diff", shadow_fn)
    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", schedule_fn)

    out = mod.evaluate_ingredients(["water"], ["vegan"])
    assert out is ike2_v
    ike2_fn.assert_called_once()
    legacy_fn.assert_not_called()
    shadow_fn.assert_not_called()
    schedule_fn.assert_called_once()
