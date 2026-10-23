"""scripts/soak_local.py: capped local /health + evaluate loop (not run in CI by default)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "soak_local.py"


def _load():
    spec = importlib.util.spec_from_file_location("soak_local", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_cap_is_small():
    mod = _load()
    assert 1 <= int(mod.DEFAULT_CAP) <= 50


def test_in_process_loop_honors_cap_and_hits_health(tmp_path):
    mod = _load()
    out = tmp_path / "soak.json"
    rc = mod.main(["--in-process", "--cap", "3", "--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["health_ok"] is True
    assert report["evaluate_n"] == 3
    assert report["http_500"] == 0
    assert report["cap"] == 3


def test_unreachable_local_server_does_not_hang(monkeypatch, tmp_path):
    mod = _load()

    def boom(*_a, **_k):
        raise ConnectionError("refused")

    monkeypatch.setattr(mod, "_http_get_json", boom)
    out = tmp_path / "soak.json"
    rc = mod.main(
        ["--base-url", "http://127.0.0.1:9", "--cap", "2", "--out", str(out)]
    )
    assert rc != 0
    assert out.exists()
    report = json.loads(out.read_text())
    assert report["health_ok"] is False
