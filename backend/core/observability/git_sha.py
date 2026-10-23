"""Resolve the running release SHA. Never raises."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_ENV_KEYS = (
    "GIT_SHA",
    "GITHUB_SHA",
    "VERCEL_GIT_COMMIT_SHA",
    "SOURCE_VERSION",
    "COMMIT_SHA",
)


def git_sha(*, short: bool = False) -> str:
    """Return the deploy git SHA, or ``unknown`` if it cannot be resolved."""
    for key in _ENV_KEYS:
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return raw[:12] if short else raw
    try:
        root = Path(__file__).resolve().parents[3]
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        sha = out.decode("ascii", errors="replace").strip()
        if sha:
            return sha[:12] if short else sha
    except Exception:
        pass
    return "unknown"
