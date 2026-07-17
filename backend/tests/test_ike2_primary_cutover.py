import importlib

import pytest


def _reload_config(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("IKE2_MODE", raising=False)
    else:
        monkeypatch.setenv("IKE2_MODE", value)
    import core.config as config
    return importlib.reload(config)


@pytest.mark.parametrize("raw", [None, "", "off", "shadow", "fallback", "PRIMARY", "garbage"])
def test_ike2_mode_coerces_to_primary(monkeypatch, raw):
    cfg = _reload_config(monkeypatch, raw)
    assert cfg.IKE2_MODE == "primary"
