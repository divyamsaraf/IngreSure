from types import SimpleNamespace

from core.knowledge.ike2.shadow import runner
from core.knowledge.ike2.shadow.runner import run_legacy_diff


def test_run_legacy_diff_runs_without_mode_gate(monkeypatch):
    """No IKE2_MODE check -- the comparison always runs when called."""
    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    diff = run_legacy_diff(["water"], ["vegan"], None, "SAFE", writer=calls.append)
    assert diff is not None
    assert diff["match"] is True
    assert calls == []


def test_logs_divergence_only(monkeypatch):
    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "UNCERTAIN")
    calls = []
    diff = run_legacy_diff(["mystery"], ["vegan"], None, "SAFE", writer=calls.append)
    assert diff["match"] is False
    assert len(calls) == 1
    assert calls[0]["legacy_verdict"] == "UNCERTAIN"
    assert calls[0]["ike2_verdict"] == "SAFE"


def test_does_not_log_when_verdicts_match(monkeypatch):
    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    diff = run_legacy_diff(["water"], ["vegan"], None, "SAFE", writer=calls.append)
    assert diff["match"] is True
    assert calls == []


def test_logs_comparison_on_every_run(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "SAFE")
    with caplog.at_level(logging.INFO, logger="core.knowledge.ike2.shadow.runner"):
        run_legacy_diff(["water"], ["vegan"], None, "SAFE", writer=lambda d: None)
    assert any("IKE2_DIFF legacy=SAFE primary=SAFE match=True" in r.message for r in caplog.records)


def test_flags_false_safe_regression(monkeypatch):
    # Primary (IKE-2) said SAFE, legacy said NOT_SAFE -> the one disagreement that can harm.
    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "NOT_SAFE")
    calls = []
    run_legacy_diff(["peanut"], ["peanut_allergy"], None, "SAFE", writer=calls.append)
    assert calls[0]["false_safe_regression"] is True


def test_accepts_enum_like_primary_verdict(monkeypatch):
    monkeypatch.setattr(runner, "legacy_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    primary = SimpleNamespace(value="UNCERTAIN")  # VerdictStatus-like
    run_legacy_diff(["x"], ["vegan"], None, primary, writer=calls.append)
    assert calls[0]["ike2_verdict"] == "UNCERTAIN"


def test_never_raises_on_internal_error(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("legacy engine exploded")

    monkeypatch.setattr(runner, "legacy_external_verdict", _boom)
    # Must swallow and return None rather than propagate into the primary path.
    assert run_legacy_diff(["x"], ["vegan"], None, "SAFE", writer=lambda d: None) is None


def test_real_pipeline_e471_vegan_not_safe():
    verdict = runner.ike2_external_verdict(["E471"], ["vegan"], None)
    assert verdict != "SAFE"


def test_real_pipeline_unknown_is_uncertain():
    verdict = runner.ike2_external_verdict(["totally_unknown_xyz"], ["vegan"], None)
    assert verdict == "UNCERTAIN"


def test_real_legacy_pipeline_gelatin_vegan_not_safe():
    verdict = runner.legacy_external_verdict(["gelatin"], ["vegan"], None)
    assert verdict == "NOT_SAFE"
