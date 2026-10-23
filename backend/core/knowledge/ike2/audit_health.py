"""Last-successful Item 12 live audit age (health-check surface)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_STAMP_PATH = _REPO / "docs" / "item12_last_live_audit.json"
_MAX_AGE_HOURS = float(os.environ.get("IKE2_LIVE_AUDIT_MAX_AGE_HOURS") or "36")


def record_live_audit_success(report_path: Path | None = None) -> dict:
    """Write stamp after a successful live audit run."""
    now = datetime.now(timezone.utc)
    payload = {
        "status": "ok",
        "completed_at": now.isoformat(),
        "report": str(report_path) if report_path else None,
    }
    _STAMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STAMP_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def db_health() -> dict:
    """Probe configured DB for GET /health. Never SAFE; down → UNCERTAIN.

    Does not increment the degraded counter (k8s probes would pump it).
    Resolve/evaluate paths call ``core.degraded.record`` on DB failure.
    """
    from core.degraded import snapshot
    from core.models.verdict import VerdictStatus

    uncertain = VerdictStatus.UNCERTAIN.value
    try:
        from core.knowledge.ingredient_db import IngredientKnowledgeDB

        db = IngredientKnowledgeDB()
        if not db.enabled:
            return {
                "db_reachable": None,
                "ike2_status": uncertain,
                "degraded": snapshot(),
            }
        ok = bool(db.ping())
        return {
            "db_reachable": ok,
            "ike2_status": "ok" if ok else uncertain,
            "degraded": snapshot(),
        }
    except Exception:
        return {
            "db_reachable": False,
            "ike2_status": uncertain,
            "degraded": snapshot(),
        }


def live_audit_health() -> dict:
    """Fields merged into GET /health for ops visibility."""
    if not _STAMP_PATH.exists():
        return {
            "ike2_live_audit": {
                "status": "never",
                "age_hours": None,
                "stale": True,
                "stamp_path": str(_STAMP_PATH),
            }
        }
    try:
        data = json.loads(_STAMP_PATH.read_text(encoding="utf-8"))
        completed = datetime.fromisoformat(data["completed_at"])
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - completed).total_seconds() / 3600.0
        stale = age_h > _MAX_AGE_HOURS
        return {
            "ike2_live_audit": {
                "status": "stale" if stale else "ok",
                "age_hours": round(age_h, 2),
                "stale": stale,
                "completed_at": data.get("completed_at"),
                "max_age_hours": _MAX_AGE_HOURS,
            }
        }
    except Exception as exc:
        return {
            "ike2_live_audit": {
                "status": "error",
                "age_hours": None,
                "stale": True,
                "error": str(exc),
            }
        }
