#!/usr/bin/env python3
"""CI: CODEOWNERS must cover license allowlist + reviewed-negatives.

Also prints a git diff of those files vs origin/main when available so a
reviewed PR is the only intended change path.

Usage (from backend/ or repo root):
    python scripts/check_governance_protected_files.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
_CODEOWNERS = _REPO / ".github" / "CODEOWNERS"

PROTECTED = (
    "backend/core/knowledge/ike2/etl/license_allowlist.json",
    "backend/core/knowledge/ike2/etl/license_attribution.json",
    "data/ike2_reviewed_negatives.json",
)


def _codeowners_text() -> str:
    if not _CODEOWNERS.is_file():
        raise FileNotFoundError(f"missing {_CODEOWNERS}")
    return _CODEOWNERS.read_text(encoding="utf-8")


def codeowners_covers_protected(text: str | None = None) -> list[str]:
    raw = text if text is not None else _codeowners_text()
    missing = []
    for path in PROTECTED:
        if path not in raw:
            missing.append(path)
    return missing


def diff_protected_vs_base(base: str = "origin/main") -> str:
    try:
        proc = subprocess.run(
            ["git", "diff", "--", *PROTECTED],
            cwd=_REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        vs_base = subprocess.run(
            ["git", "diff", f"{base}...HEAD", "--", *PROTECTED],
            cwd=_REPO,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    chunks = []
    if proc.stdout.strip():
        chunks.append(proc.stdout)
    if vs_base.returncode == 0 and vs_base.stdout.strip():
        chunks.append(vs_base.stdout)
    return "\n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        missing = codeowners_covers_protected()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    if missing:
        print("CODEOWNERS missing protected paths:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    print("CODEOWNERS covers:")
    for path in PROTECTED:
        print(f"  {path}")
    diff = diff_protected_vs_base()
    if diff.strip():
        print("Protected-file diff (must land only via a reviewed PR):")
        print(diff)
    else:
        print("No local/base diff on protected files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
