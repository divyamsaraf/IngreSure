"""Item 23: Celery Beat is configured in-app and embedded in the compose worker."""
from __future__ import annotations

import re
from pathlib import Path

from worker.celery_app import celery_app

_COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"


def test_beat_schedule_targets_registered_enrich_task():
    import worker.tasks  # noqa: F401  (registers tasks, as include= does in the worker)

    schedule = celery_app.conf.beat_schedule
    [entry] = [e for e in schedule.values() if e["task"] == "enrich_unknown_batch"]
    assert float(entry["schedule"]) > 0
    assert "enrich_unknown_batch" in celery_app.tasks


def test_worker_process_imports_tasks():
    assert "worker.tasks" in (celery_app.conf.include or ())


def test_compose_worker_runs_embedded_beat_only():
    text = _COMPOSE.read_text()
    worker_block = text.split("\n  worker:\n", 1)[1].split("\n  frontend:\n", 1)[0]
    command = re.search(r"^\s+command: (.+)$", worker_block, re.M).group(1)
    assert '"worker"' in command and '"-B"' in command
    # No second scheduler service.
    assert '"beat"' not in text
