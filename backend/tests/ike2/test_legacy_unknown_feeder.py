"""Item 33 Prompt 4: legacy log_unknown must not write unknown_ingredients."""
from __future__ import annotations

from core.enrichment.unknown_log import UnknownIngredientsLog
from core.knowledge.ike2 import unknown_queue as uq
from tests.ike2.fake_supabase import FakeSupabase


def test_record_enqueues_ike2_not_legacy_table(tmp_path, monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(uq, "_default_client", lambda: fake)
    legacy = []
    monkeypatch.setattr(
        "core.knowledge.ingredient_db.IngredientKnowledgeDB.upsert_unknown_ingredient",
        lambda self, **kwargs: legacy.append(kwargs),
    )
    log = UnknownIngredientsLog(path=tmp_path / "unknown.json")
    log.record("dragon fruit powder", "dragon fruit powder")

    assert legacy == []
    assert "unknown_ingredients" not in fake.touched()
    [row] = fake.tables[uq.TABLE]
    assert row["normalized_key"] == "dragon fruit powder"
    assert row["status"] == "pending"
    assert row["frequency"] == 1


def test_junk_key_is_not_enqueued(tmp_path, monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(uq, "_default_client", lambda: fake)
    log = UnknownIngredientsLog(path=tmp_path / "unknown.json")
    log.record("zyzzx unknown starch q99", "zyzzx unknown starch q99")
    assert fake.calls == []
