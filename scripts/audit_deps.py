#!/usr/bin/env python3
"""Wrap pip-audit and npm audit; write a report. Default exit 0 (non-blocking).

Historical CVEs must not fail the main CI job. Use --strict to fail on findings.
Never talks to production. Run from repo root:

  python scripts/audit_deps.py --out backend/.local_reports/dep_audit.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BACKEND = _REPO / "backend"
_FRONTEND = _REPO / "frontend"
_DEFAULT_OUT = _BACKEND / ".local_reports" / "dep_audit.json"


def _run(cmd: list[str], *, cwd: Path) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        return {"status": "missing", "cmd": cmd, "returncode": None}
    except Exception as exc:
        return {"status": "error", "cmd": cmd, "error": str(exc), "returncode": None}
    findings = proc.returncode not in (0, None)
    return {
        "status": "findings" if findings else "clean",
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    parser.add_argument("--python-only", action="store_true")
    parser.add_argument("--npm-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on findings")
    args = parser.parse_args(argv)

    tools: dict[str, dict] = {}
    if not args.npm_only:
        req = _BACKEND / "requirements.txt"
        tools["python"] = _run(
            ["pip-audit", "-r", str(req), "-f", "json"],
            cwd=_BACKEND,
        )
    if not args.python_only:
        tools["npm"] = _run(["npm", "audit", "--json"], cwd=_FRONTEND)

    report = {
        "exit_policy": "strict" if args.strict else "report_only",
        "tools": tools,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    if args.strict and any(t.get("status") == "findings" for t in tools.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
