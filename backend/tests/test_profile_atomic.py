"""JSON profile store: atomic replace, corrupt file never wiped, snapshot read-only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.models.user_profile import UserProfile


@pytest.fixture
def profile_path(monkeypatch, tmp_path):
    path = tmp_path / "profiles.json"
    monkeypatch.setattr("core.profile_storage._PROFILES_PATH", path)
    import core.profile_storage as ps

    with ps._profile_cache_lock:
        ps._profile_cache.clear()
    yield path
    with ps._profile_cache_lock:
        ps._profile_cache.clear()


def test_save_is_atomic_temp_plus_rename(profile_path, monkeypatch):
    import core.profile_storage as ps

    seen: list[str] = []
    real_replace = ps.os.replace

    def _track(src, dst):
        seen.append(Path(src).name)
        return real_replace(src, dst)

    monkeypatch.setattr(ps.os, "replace", _track)
    ps.save_profile(UserProfile(user_id="test_u1", dietary_preference="Vegan"))
    assert profile_path.exists()
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    assert data["user:test_u1"]["dietary_preference"] == "Vegan"
    assert seen, "save must go through os.replace"


def test_corrupt_json_does_not_wipe_on_save(profile_path):
    import core.profile_storage as ps

    profile_path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        ps.save_profile(UserProfile(user_id="test_u2"))
    assert profile_path.read_text(encoding="utf-8") == "{not-json"


def test_snapshot_path_is_read_only(profile_path, tmp_path, monkeypatch):
    import core.profile_storage as ps

    snap = tmp_path / "snap.json"
    snap.write_text(
        json.dumps({"user:test_snap": {"dietary_preference": "Halal", "allergens": [], "lifestyle": []}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PROFILE_SNAPSHOT_PATH", str(snap))
    monkeypatch.setenv("PROFILE_READ_ONLY", "1")
    got = ps.get_profile("test_snap")
    assert got is not None
    assert got.dietary_preference == "Halal"
    ps.save_profile(UserProfile(user_id="test_snap", dietary_preference="Vegan"))
    loaded = json.loads(snap.read_text(encoding="utf-8"))
    assert loaded["user:test_snap"]["dietary_preference"] == "Halal"
