"""scripts/audit_deps.py wraps pip-audit + npm audit and writes a report without failing CI."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "audit_deps.py"


def _load():
    spec = importlib.util.spec_from_file_location("audit_deps", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_historical_vulns_do_not_fail_default_exit(tmp_path, monkeypatch):
    mod = _load()

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = json.dumps({"vulnerabilities": {"x": {"severity": "high"}}})
            stderr = "found"
        return R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    out = tmp_path / "dep_audit.json"
    rc = mod.main(["--out", str(out), "--python-only"])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["exit_policy"] == "report_only"
    assert "python" in report["tools"]


def test_strict_mode_fails_on_findings(tmp_path, monkeypatch):
    mod = _load()

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = "{}"
            stderr = "vuln"
        return R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    out = tmp_path / "dep_audit.json"
    rc = mod.main(["--out", str(out), "--npm-only", "--strict"])
    assert rc != 0


def test_missing_toolchain_is_recorded_not_crash(tmp_path, monkeypatch):
    mod = _load()

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    out = tmp_path / "dep_audit.json"
    rc = mod.main(["--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["tools"]["python"]["status"] in {"missing", "error"}
    assert report["tools"]["npm"]["status"] in {"missing", "error"}
