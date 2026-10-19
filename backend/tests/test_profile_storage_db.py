"""USE_PROFILE_DB path: profiles go to public.users, not profiles.json."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.models.user_profile import UserProfile


UUID_USER = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def enable_profile_db(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_PROFILE_DB", "1")
    path = tmp_path / "profiles.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("core.profile_storage._PROFILES_PATH", path)
    # clear cache between tests
    import core.profile_storage as ps

    with ps._profile_cache_lock:
        ps._profile_cache.clear()
    return path


def test_use_profile_db_flag(monkeypatch):
    import core.profile_storage as ps

    monkeypatch.delenv("USE_PROFILE_DB", raising=False)
    assert ps.use_profile_db() is False
    monkeypatch.setenv("USE_PROFILE_DB", "supabase")
    assert ps.use_profile_db() is True


def test_db_save_and_get_does_not_touch_json(enable_profile_db, monkeypatch):
    import core.profile_storage as ps

    store: dict[str, dict] = {}

    class _Table:
        def __init__(self, name):
            self.name = name
            self._filters = {}
            self._payload = None
            self._op = None

        def select(self, *_a, **_k):
            self._op = "select"
            return self

        def eq(self, k, v):
            self._filters[k] = v
            return self

        def limit(self, *_a, **_k):
            return self

        def update(self, payload):
            self._op = "update"
            self._payload = payload
            return self

        def insert(self, payload):
            self._op = "insert"
            self._payload = payload
            return self

        def execute(self):
            if self._op == "select":
                uid = self._filters.get("id")
                row = store.get(uid)
                return SimpleNamespace(data=[row] if row else [])
            if self._op == "insert":
                store[self._payload["id"]] = dict(self._payload)
                return SimpleNamespace(data=[self._payload])
            if self._op == "update":
                uid = self._filters.get("id")
                store.setdefault(uid, {"id": uid, "preferences": {}})
                store[uid].update(self._payload)
                return SimpleNamespace(data=[store[uid]])
            return SimpleNamespace(data=[])

    client = MagicMock()
    client.table.side_effect = lambda name: _Table(name)
    monkeypatch.setattr(ps, "_db_client", lambda: client)

    profile = UserProfile(
        user_id=UUID_USER,
        dietary_preference="Jain",
        allergens=["Peanuts"],
        lifestyle=["Gluten-Free"],
    )
    ps.save_profile(profile)

    # JSON file must stay empty / unused for UUID under DB mode
    assert enable_profile_db.read_text(encoding="utf-8").strip() in ("{}", "")
    assert UUID_USER in store
    assert store[UUID_USER]["diet_type"] == "Jain"
    assert store[UUID_USER]["allergies"] == ["Peanuts"]
    assert store[UUID_USER]["preferences"]["lifestyle"] == ["Gluten-Free"]

    with ps._profile_cache_lock:
        ps._profile_cache.clear()
    loaded = ps.get_profile(UUID_USER)
    assert loaded is not None
    assert loaded.dietary_preference == "Jain"
    assert loaded.allergens == ["Peanuts"]
    assert loaded.lifestyle == ["Gluten-Free"]


def test_non_uuid_still_uses_json_when_db_enabled(enable_profile_db, monkeypatch):
    import core.profile_storage as ps

    monkeypatch.setattr(
        ps,
        "_db_client",
        lambda: (_ for _ in ()).throw(AssertionError("DB must not be used for non-UUID")),
    )
    ps.save_profile(
        UserProfile(user_id="anon-test-user", dietary_preference="Vegan", allergens=[], lifestyle=[])
    )
    data = enable_profile_db.read_text(encoding="utf-8")
    assert "anon-test-user" in data or "user:anon-test-user" in data
    loaded = ps.get_profile("anon-test-user")
    assert loaded is not None
    assert loaded.dietary_preference == "Vegan"


def test_org_profiles_stay_on_json_when_db_enabled(enable_profile_db, monkeypatch):
    import core.profile_storage as ps

    monkeypatch.setattr(
        ps,
        "_db_client",
        lambda: (_ for _ in ()).throw(AssertionError("DB must not be used for org profiles")),
    )
    ps.save_profile(
        UserProfile(user_id=UUID_USER, dietary_preference="Halal"),
        org_id="org_a",
    )
    assert "org:org_a:user:" in enable_profile_db.read_text(encoding="utf-8")
