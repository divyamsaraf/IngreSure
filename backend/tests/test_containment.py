"""Flip-window containment: queue writes and worker beat can be switched off."""
from __future__ import annotations

from tests.ike2.fake_supabase import FakeSupabase


def test_unknown_queue_disabled_skips_writes(monkeypatch):
    from core.knowledge.ike2 import unknown_queue as uq

    monkeypatch.setenv("UNKNOWN_QUEUE_ENABLED", "0")
    fake = FakeSupabase()
    assert uq.enqueue_unknown("oat drink", "Oat Drink", client=fake) is False
    assert fake.tables.get(uq.TABLE, []) == []


def test_unknown_queue_enabled_still_writes(monkeypatch):
    from core.knowledge.ike2 import unknown_queue as uq

    monkeypatch.setenv("UNKNOWN_QUEUE_ENABLED", "1")
    fake = FakeSupabase()
    assert uq.enqueue_unknown("oat drink", "Oat Drink", client=fake) is True
    assert fake.tables[uq.TABLE][0]["normalized_key"] == "oat drink"


def test_worker_disabled_clears_beat():
    from worker.celery_app import beat_schedule

    assert beat_schedule(enabled=False) == {}
    assert "enrich-unknown-batch-hourly" in beat_schedule(enabled=True)


def test_cleanup_dry_run_lists_test_prefix_only(tmp_path, monkeypatch):
    import json

    from scripts import cleanup_test_data as ctd

    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "user:test_flip_1": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
                "user:real_user": {"dietary_preference": "Halal", "allergens": [], "lifestyle": []},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ctd, "_PROFILES_PATH", path)
    report = ctd.cleanup_profiles(dry_run=True, prefix="test_")
    assert report["would_delete"] == ["user:test_flip_1"]
    leftover = json.loads(path.read_text(encoding="utf-8"))
    assert "user:test_flip_1" in leftover
    assert "user:real_user" in leftover
    report = ctd.cleanup_profiles(dry_run=False, prefix="test_")
    leftover = json.loads(path.read_text(encoding="utf-8"))
    assert "user:test_flip_1" not in leftover
    assert leftover["user:real_user"]["dietary_preference"] == "Halal"
