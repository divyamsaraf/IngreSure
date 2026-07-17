from types import SimpleNamespace

from core import config
from core.knowledge.ike2.shadow import runner
from core.knowledge.ike2.shadow.runner import run_shadow


def _shadow(monkeypatch):
    monkeypatch.setattr(config, "IKE2_MODE", "shadow")


def test_noop_when_mode_off(monkeypatch):
    monkeypatch.setattr(config, "IKE2_MODE", "off")
    calls = []
    out = run_shadow(["water"], ["vegan"], None, "SAFE", writer=calls.append)
    assert out is None
    assert calls == []


def test_logs_divergence_only(monkeypatch):
    _shadow(monkeypatch)
    monkeypatch.setattr(runner, "ike2_external_verdict", lambda *a, **k: "UNCERTAIN")
    calls = []
    diff = run_shadow(["mystery"], ["vegan"], None, "SAFE", writer=calls.append)
    assert diff["match"] is False
    assert len(calls) == 1
    assert calls[0]["legacy_verdict"] == "SAFE"
    assert calls[0]["ike2_verdict"] == "UNCERTAIN"


def test_does_not_log_when_verdicts_match(monkeypatch):
    _shadow(monkeypatch)
    monkeypatch.setattr(runner, "ike2_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    diff = run_shadow(["water"], ["vegan"], None, "SAFE", writer=calls.append)
    assert diff["match"] is True
    assert calls == []


def test_logs_comparison_on_every_shadow_run(monkeypatch, caplog):
    import logging

    _shadow(monkeypatch)
    monkeypatch.setattr(runner, "ike2_external_verdict", lambda *a, **k: "SAFE")
    with caplog.at_level(logging.INFO, logger="core.knowledge.ike2.shadow.runner"):
        run_shadow(["water"], ["vegan"], None, "SAFE", writer=lambda d: None)
    assert any("IKE2_SHADOW legacy=SAFE ike2=SAFE match=True" in r.message for r in caplog.records)


def test_flags_false_safe_regression(monkeypatch):
    _shadow(monkeypatch)
    # Legacy said NOT_SAFE, IKE-2 said SAFE -> the one disagreement that can harm.
    monkeypatch.setattr(runner, "ike2_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    run_shadow(["peanut"], ["peanut_allergy"], None, "NOT_SAFE", writer=calls.append)
    assert calls[0]["false_safe_regression"] is True


def test_accepts_enum_like_legacy_verdict(monkeypatch):
    _shadow(monkeypatch)
    monkeypatch.setattr(runner, "ike2_external_verdict", lambda *a, **k: "SAFE")
    calls = []
    legacy = SimpleNamespace(value="UNCERTAIN")  # VerdictStatus-like
    run_shadow(["x"], ["vegan"], None, legacy, writer=calls.append)
    assert calls[0]["legacy_verdict"] == "UNCERTAIN"


def test_never_raises_on_internal_error(monkeypatch):
    _shadow(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("resolver exploded")

    monkeypatch.setattr(runner, "ike2_external_verdict", _boom)
    # Must swallow and return None rather than propagate into the legacy path.
    assert run_shadow(["x"], ["vegan"], None, "SAFE", writer=lambda d: None) is None


def test_real_pipeline_e471_vegan_not_safe(monkeypatch):
    _shadow(monkeypatch)
    verdict = runner.ike2_external_verdict(["E471"], ["vegan"], None)
    assert verdict != "SAFE"


def test_real_pipeline_unknown_is_uncertain(monkeypatch):
    _shadow(monkeypatch)
    verdict = runner.ike2_external_verdict(["totally_unknown_xyz"], ["vegan"], None)
    assert verdict == "UNCERTAIN"
