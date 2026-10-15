"""Item 4.1 Prompt 4: decay planner + CLI dry-run with fake clock."""
from datetime import datetime, timedelta, timezone

from core.knowledge.ike2.decay import TTL_AUTO_CLASSIFIED_DAYS, TTL_VERIFIED_DAYS, plan_decay_row
from scripts.ike2_decay_knowledge import plan_decays


def _ts(days_ago: float, *, as_of: datetime) -> str:
    return (as_of - timedelta(days=days_ago)).isoformat()


def test_plan_decay_row_respects_fake_clock():
    as_of = datetime(2026, 9, 18, tzinfo=timezone.utc)
    assert (
        plan_decay_row(
            knowledge_state="VERIFIED",
            trust_refreshed_at=_ts(TTL_VERIFIED_DAYS - 1, as_of=as_of),
            as_of=as_of,
        )
        is None
    )
    assert (
        plan_decay_row(
            knowledge_state="VERIFIED",
            trust_refreshed_at=_ts(TTL_VERIFIED_DAYS, as_of=as_of),
            as_of=as_of,
        )
        == "AUTO_CLASSIFIED"
    )


def test_plan_decays_batch_dry_logic():
    as_of = datetime(2026, 9, 18, tzinfo=timezone.utc)
    rows = [
        {
            "id": "1",
            "canonical_name": "old_verified",
            "knowledge_state": "VERIFIED",
            "trust_refreshed_at": _ts(TTL_VERIFIED_DAYS + 5, as_of=as_of),
        },
        {
            "id": "2",
            "canonical_name": "fresh",
            "knowledge_state": "VERIFIED",
            "trust_refreshed_at": _ts(1, as_of=as_of),
        },
        {
            "id": "3",
            "canonical_name": "old_auto",
            "knowledge_state": "AUTO_CLASSIFIED",
            "trust_refreshed_at": _ts(TTL_AUTO_CLASSIFIED_DAYS + 1, as_of=as_of),
        },
        {
            "id": "4",
            "canonical_name": "locked_ignored",
            "knowledge_state": "LOCKED",
            "trust_refreshed_at": _ts(10_000, as_of=as_of),
        },
    ]
    planned = plan_decays(rows, as_of=as_of)
    by_name = {p["canonical_name"]: p["to_state"] for p in planned}
    assert by_name == {
        "old_verified": "AUTO_CLASSIFIED",
        "old_auto": "DISCOVERED",
    }


def test_cli_dry_run_default_does_not_write(monkeypatch):
    """CLI default is dry-run: plan only, never call update."""
    from scripts import ike2_decay_knowledge as cli

    as_of = datetime(2026, 9, 18, tzinfo=timezone.utc)
    fake_rows = [
        {
            "id": "g1",
            "canonical_name": "stale",
            "knowledge_state": "VERIFIED",
            "trust_refreshed_at": _ts(TTL_VERIFIED_DAYS + 1, as_of=as_of),
        }
    ]
    updates = []

    class _FakeClient:
        def table(self, name):
            assert name == "ike2_ingredient_groups"
            return self

        def select(self, *_a, **_k):
            return self

        def in_(self, *_a, **_k):
            return self

        def update(self, payload):
            updates.append(payload)
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            return type("R", (), {"data": fake_rows})()

    class _FakeDB:
        enabled = True
        _client = _FakeClient()

    monkeypatch.setattr(
        "core.knowledge.ingredient_db.IngredientKnowledgeDB", lambda: _FakeDB()
    )
    assert cli.main(["--as-of", as_of.isoformat()]) == 0
    assert updates == []
