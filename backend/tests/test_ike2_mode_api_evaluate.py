"""Evaluate endpoints always serve IKE-2 (Item 16 Prompt 7; IKE2_MODE retired)."""
from __future__ import annotations

from unittest.mock import MagicMock

from core.models.verdict import ComplianceVerdict, VerdictStatus


def _verdict(status: str) -> ComplianceVerdict:
    return ComplianceVerdict(status=VerdictStatus(status))


def test_evaluate_always_serves_ike2(monkeypatch):
    from core.api import v1_evaluate as mod

    ike2_v = _verdict("SAFE")
    ike2_fn = MagicMock(return_value=(ike2_v, [{"id": "water"}]))
    monkeypatch.setattr(mod, "_run_ike2_evaluate_with_flags", ike2_fn)

    out = mod.evaluate_ingredients(["water"], ["vegan"])
    assert out is ike2_v
    ike2_fn.assert_called_once()


def test_get_ike2_mode_removed():
    import core.config as cfg

    assert not hasattr(cfg, "get_ike2_mode")
    assert not hasattr(cfg, "IKE2_MODE")
