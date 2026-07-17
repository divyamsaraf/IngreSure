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


def test_skips_during_interpreter_finalization(monkeypatch):
    monkeypatch.setattr(runner, "_interpreter_finalizing", lambda: True)

    def _boom(*a, **k):
        raise AssertionError("legacy engine should not run during finalization")

    monkeypatch.setattr(runner, "legacy_external_verdict", _boom)
    assert run_legacy_diff(["x"], ["vegan"], None, "SAFE", writer=lambda d: None) is None


def test_swallows_interpreter_shutdown_runtime_error(monkeypatch):
    monkeypatch.setattr(runner, "_interpreter_finalizing", lambda: False)

    def _shutdown_race(*a, **k):
        raise RuntimeError("cannot schedule new futures after interpreter shutdown")

    monkeypatch.setattr(runner, "legacy_external_verdict", _shutdown_race)
    assert run_legacy_diff(["x"], ["vegan"], None, "SAFE", writer=lambda d: None) is None


def test_log_diff_skips_during_interpreter_finalization(monkeypatch):
    import core.knowledge.ingredient_db as ingredient_db

    monkeypatch.setattr(runner, "_interpreter_finalizing", lambda: True)

    def _boom():
        raise AssertionError("supabase client should not be created during finalization")

    monkeypatch.setattr(ingredient_db, "get_supabase_config", _boom)
    runner._log_diff(
        {
            "raw_input": "x",
            "legacy_verdict": "SAFE",
            "ike2_verdict": "SAFE",
            "match": True,
            "false_safe_regression": False,
        }
    )


def test_real_pipeline_e471_vegan_not_safe():
    verdict = runner.ike2_external_verdict(["E471"], ["vegan"], None)
    assert verdict != "SAFE"


def test_real_pipeline_unknown_is_uncertain():
    verdict = runner.ike2_external_verdict(["totally_unknown_xyz"], ["vegan"], None)
    assert verdict == "UNCERTAIN"


def test_real_legacy_pipeline_gelatin_vegan_not_safe():
    verdict = runner.legacy_external_verdict(["gelatin"], ["vegan"], None)
    assert verdict == "NOT_SAFE"


def test_legacy_external_verdict_does_not_call_bridge_run_new_engine_chat(monkeypatch):
    """Regression guard: once bridge's chat entrypoint is IKE-2-only, calling
    it here would compare IKE-2 to itself instead of running the legacy
    engine. legacy_external_verdict must call ComplianceEngine directly.
    """
    import core.bridge as bridge

    def _boom(*a, **k):
        raise AssertionError("legacy_external_verdict must not call run_new_engine_chat")

    monkeypatch.setattr(bridge, "run_new_engine_chat", _boom)
    verdict = runner.legacy_external_verdict(["gelatin"], ["vegan"], None)
    assert verdict == "NOT_SAFE"


def test_legacy_external_verdict_uses_compliance_engine_directly(monkeypatch):
    """legacy_external_verdict must instantiate ComplianceEngine itself
    rather than delegating to core.bridge.run_new_engine_chat.
    """
    import core.evaluation.compliance_engine as compliance_engine_module

    calls = []
    real_evaluate = compliance_engine_module.ComplianceEngine.evaluate

    def _spy_evaluate(self, *args, **kwargs):
        calls.append((args, kwargs))
        return real_evaluate(self, *args, **kwargs)

    monkeypatch.setattr(
        compliance_engine_module.ComplianceEngine, "evaluate", _spy_evaluate
    )
    verdict = runner.legacy_external_verdict(["gelatin"], ["vegan"], None)
    assert verdict == "NOT_SAFE"
    assert len(calls) == 1
    assert calls[0][1].get("use_api_fallback") is False
