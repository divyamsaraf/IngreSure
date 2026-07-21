#!/usr/bin/env python3
"""
Secrets hygiene gate: fails (exit 1) if any Supabase service-role secret pattern
appears where the frontend (a browser-shipped bundle) could ever see it.

Checks:
  1. Any file under frontend/ (excluding node_modules, .next) contains
     SERVICE_ROLE or service_role_key (case-insensitive) — these must never
     reach client-shipped code.
  2. Any NEXT_PUBLIC_*SERVICE* or NEXT_PUBLIC_*SECRET* env var name appears in a
     tracked frontend .env.example / .env* file — NEXT_PUBLIC_ vars are inlined
     into the client bundle at build time, so a secret with that prefix would ship
     to every visitor's browser.

Usage (from repo root or from backend/, both work):
    python scripts/check_secrets_hygiene.py       # from backend/
    python backend/scripts/check_secrets_hygiene.py  # from repo root

Exit codes: 0 = clean, 1 = violation(s) found (printed to stderr).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# backend/scripts/check_secrets_hygiene.py -> parent=scripts, parent.parent=backend, parent.parent.parent=repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIR = _REPO_ROOT / "frontend"

_EXCLUDED_DIR_NAMES = {"node_modules", ".next", ".git"}

_SERVICE_ROLE_RE = re.compile(r"service_role", re.IGNORECASE)
_NEXT_PUBLIC_SECRET_RE = re.compile(r"NEXT_PUBLIC_\w*(SERVICE|SECRET)\w*", re.IGNORECASE)

# Binary/asset extensions not worth scanning as text.
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2", ".ttf",
    ".eot", ".webp", ".mp4", ".pdf", ".lock",
}


def _relative_label(path: Path) -> str:
    """Best-effort path label for messages: relative to repo root when possible, else absolute."""
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def _iter_frontend_files():
    if not _FRONTEND_DIR.exists():
        return
    for path in _FRONTEND_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        yield path


def _check_service_role_in_frontend() -> list[str]:
    """Check 1: no SERVICE_ROLE / service_role_key pattern anywhere under frontend/."""
    violations = []
    for path in _iter_frontend_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if _SERVICE_ROLE_RE.search(text):
            violations.append(f"{_relative_label(path)}: matches SERVICE_ROLE / service_role pattern")
    return violations


def _check_next_public_secret_env_vars() -> list[str]:
    """Check 2: no NEXT_PUBLIC_*SERVICE* / NEXT_PUBLIC_*SECRET* var name in frontend .env* files."""
    violations = []
    if not _FRONTEND_DIR.exists():
        return violations
    for path in _FRONTEND_DIR.glob(".env*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in _NEXT_PUBLIC_SECRET_RE.finditer(text):
            violations.append(f"{_relative_label(path)}: disallowed env var name '{match.group(0)}'")
    return violations


def main() -> int:
    violations = _check_service_role_in_frontend() + _check_next_public_secret_env_vars()
    if violations:
        print("Secrets hygiene check FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(
            "\nSERVICE_ROLE / service_role keys and NEXT_PUBLIC_*SERVICE*/*SECRET* env vars "
            "must never appear in frontend/ — anything with NEXT_PUBLIC_ is inlined into the "
            "client bundle and shipped to every visitor's browser.",
            file=sys.stderr,
        )
        return 1
    print("Secrets hygiene check passed: no SERVICE_ROLE patterns or NEXT_PUBLIC_*SERVICE*/*SECRET* vars in frontend/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
