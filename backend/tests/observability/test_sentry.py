from core.observability.sentry import _before_send, init_sentry, reset_for_tests


def test_init_sentry_noop_without_dsn(monkeypatch):
    reset_for_tests()
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False


def test_init_sentry_noop_when_sdk_missing(monkeypatch):
    reset_for_tests()
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.invalid/1")
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", None)
    # Force ImportError path: hide sentry_sdk if present.
    import builtins

    real_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name.startswith("sentry_sdk"):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    assert init_sentry() is False
    reset_for_tests()


def test_before_send_scrubs_body_and_drops_pii():
    event = {
        "request": {"data": {"query": "eggs"}, "headers": {"authorization": "Bearer x"}},
        "user": {"id": "anon-1", "email": "hidden@example.com", "ip_address": "10.0.0.1"},
        "extra": {"dietary_preference": "Halal"},
    }
    out = _before_send(event)
    assert "data" not in out["request"]
    assert out["user"] == {"id": "anon-1"}
    assert out["extra"]["dietary_preference"] == "[REDACTED]"
