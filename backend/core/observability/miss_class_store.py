"""Persist miss_class tags for offline promote work. No raw ingredient text.

Default store is process-local counters plus an optional JSON file
(``OBSERVABILITY_MISS_CLASS_PATH``, default ``data/observability/miss_class.json``).
Keys are SHA-256 hashes; the raw atom is never written.

Call ``record_miss_class(tag, normalized_key=...)`` from the resolver hook
documented in docs/observability/app_hooks.md. This module does not change
verdicts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_counts: dict[str, dict[str, Any]] = {}
_path_override: Optional[Path] = None


def _default_path() -> Path:
    raw = (os.environ.get("OBSERVABILITY_MISS_CLASS_PATH") or "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[3] / "data" / "observability" / "miss_class.json"


def _store_path() -> Path:
    return _path_override or _default_path()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_normalized_key(normalized_key: str) -> str:
    return hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()


def reset_for_tests(path: Optional[Path] = None) -> None:
    global _path_override
    with _LOCK:
        _counts.clear()
        _path_override = path


def _load_unlocked(path: Path) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        by_class = data.get("by_class") or {}
        if isinstance(by_class, dict):
            for tag, row in by_class.items():
                if isinstance(row, dict):
                    _counts[str(tag)] = {
                        "count": int(row.get("count") or 0),
                        "last_seen": row.get("last_seen"),
                        "key_hashes": list(row.get("key_hashes") or [])[:50],
                    }
    except Exception as exc:
        logger.warning("miss_class store load failed: %s", exc)


def _persist_unlocked(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _now(),
        "by_class": _counts,
        "note": "key_hashes are sha256(normalized_key); raw atoms are not stored",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def record_miss_class(
    miss_class: str,
    *,
    normalized_key: Optional[str] = None,
    persist: bool = True,
) -> None:
    """Increment a miss_class counter. Never raises. Never stores raw text."""
    tag = (miss_class or "").strip()
    if not tag:
        return
    key_hash = hash_normalized_key(normalized_key) if normalized_key else None
    path = _store_path()
    try:
        with _LOCK:
            if tag not in _counts and path.exists() and not _counts:
                _load_unlocked(path)
            row = _counts.setdefault(tag, {"count": 0, "last_seen": None, "key_hashes": []})
            row["count"] = int(row.get("count") or 0) + 1
            row["last_seen"] = _now()
            if key_hash:
                hashes = list(row.get("key_hashes") or [])
                if key_hash not in hashes:
                    hashes = (hashes + [key_hash])[:50]
                row["key_hashes"] = hashes
            if persist:
                _persist_unlocked(path)
    except Exception as exc:
        logger.warning("miss_class persist failed: %s", exc)


def snapshot_miss_classes() -> dict[str, Any]:
    path = _store_path()
    with _LOCK:
        if not _counts and path.exists():
            _load_unlocked(path)
        by_class = {
            tag: {"count": int(row.get("count") or 0), "last_seen": row.get("last_seen")}
            for tag, row in _counts.items()
        }
    return {
        "by_class": by_class,
        "total": sum(v["count"] for v in by_class.values()),
        "distinct_classes": len(by_class),
    }
