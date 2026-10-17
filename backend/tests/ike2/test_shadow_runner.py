"""IKE-2 shadow runner helpers retained after legacy-diff removal (Item 16 Prompt 7)."""
from __future__ import annotations

from core.knowledge.ike2.shadow import runner
from core.knowledge.ike2.shadow.runner import ike2_external_verdict, flags_from_compliance_inputs


def test_ike2_external_verdict_gelatin_vegan_not_safe():
    assert ike2_external_verdict(["gelatin"], ["vegan"], None) == "NOT_SAFE"


def test_flags_from_compliance_inputs_includes_alcohol_role():
    class _Inp:
        flags = {"animal_origin": False}
        alcohol_role = "ingredient"

    out = flags_from_compliance_inputs([_Inp()])
    assert out == [{"animal_origin": False, "alcohol_role": "ingredient"}]


def test_log_diff_skips_when_finalizing(monkeypatch):
    monkeypatch.setattr(runner, "_interpreter_finalizing", lambda: True)
    # Must not raise or attempt network.
    runner._log_diff({"raw_input": "x", "legacy_verdict": "SAFE", "ike2_verdict": "SAFE"})
