"""Item 18: ike2_unknown_queue upsert + resolver L5 fire-and-forget hook."""
from __future__ import annotations

import logging

import core.knowledge.ike2.resolver as resolver_mod
from core.knowledge.ike2 import unknown_queue as uq
from tests.ike2.fake_supabase import FakeSupabase


def test_enqueue_inserts_pending_row():
    fake = FakeSupabase()
    assert uq.enqueue_unknown("oat drink", "Oat Drink", client=fake) is True
    rows = fake.tables[uq.TABLE]
    assert len(rows) == 1
    assert rows[0]["normalized_key"] == "oat drink"
    assert rows[0]["frequency"] == 1
    assert rows[0]["status"] == "pending"
    assert rows[0]["enrichment"]["raw_inputs"] == ["Oat Drink"]


def test_enqueue_existing_bumps_frequency_and_dedupes_raw_inputs():
    fake = FakeSupabase()
    uq.enqueue_unknown("oat drink", "Oat Drink", client=fake)
    uq.enqueue_unknown("oat drink", "Oat Drink", client=fake)
    uq.enqueue_unknown("oat drink", "oat drink", client=fake)
    rows = fake.tables[uq.TABLE]
    assert len(rows) == 1
    assert rows[0]["frequency"] == 3
    assert rows[0]["enrichment"]["raw_inputs"] == ["Oat Drink", "oat drink"]


def test_enqueue_never_touches_legacy_table():
    fake = FakeSupabase()
    uq.enqueue_unknown("oat drink", "Oat Drink", client=fake)
    assert "unknown_ingredients" not in fake.touched()


def test_junk_keys_are_skipped():
    fake = FakeSupabase()
    for key in ("a", "b", "", "zyzzx unknown starch q99"):
        assert uq.enqueue_unknown(key, key, client=fake) is False
    assert fake.calls == []


def test_write_failure_is_silent_but_logged(caplog):
    fake = FakeSupabase(fail_tables={uq.TABLE})
    with caplog.at_level(logging.WARNING, logger=uq.__name__):
        assert uq.enqueue_unknown("oat drink", "Oat Drink", client=fake) is False
    assert "IKE2_UNKNOWN_QUEUE_WRITE_FAILED" in caplog.text


def test_no_config_is_a_noop():
    # tests/conftest.py forces the default client to None.
    assert uq.enqueue_unknown("oat drink", "Oat Drink") is False


def test_record_miss_writes_in_background(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(uq, "_default_client", lambda: fake)
    monkeypatch.setattr(uq, "_executor", None)
    uq.record_miss("oat drink", "Oat Drink")
    uq._executor.shutdown(wait=True)
    monkeypatch.setattr(uq, "_executor", None)
    assert fake.tables[uq.TABLE][0]["normalized_key"] == "oat drink"


def test_record_miss_never_raises_when_submit_fails(monkeypatch):
    class _Boom:
        def submit(self, *_a, **_k):
            raise RuntimeError("pool dead")

    monkeypatch.setattr(uq, "_executor", _Boom())
    uq.record_miss("oat drink", "Oat Drink")


def _all_tiers_miss(monkeypatch):
    monkeypatch.setattr(resolver_mod.truth_anchor, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.local_ontology, "lookup", lambda _n: None)
    monkeypatch.setattr(resolver_mod.db, "disambiguate", lambda *_a, **_k: "none")
    monkeypatch.setattr(resolver_mod.db, "resolve_alias", lambda *_a, **_k: None)


def test_resolver_l5_miss_submits_queue_write_and_verdict_unchanged(monkeypatch):
    _all_tiers_miss(monkeypatch)
    calls: list = []
    monkeypatch.setattr(uq, "record_miss", lambda key, raw=None: calls.append((key, raw)))

    out = resolver_mod.resolve("Zzqx Novel Gum", None)

    assert out.status == "uncertain"
    assert out.resolution_layer == "L5_unknown_queue"
    assert out.trusted is False
    assert calls == [("zzqx novel gum", "Zzqx Novel Gum")]


def test_resolver_ambiguous_is_not_enqueued(monkeypatch):
    _all_tiers_miss(monkeypatch)
    monkeypatch.setattr(resolver_mod.db, "disambiguate", lambda *_a, **_k: "ambiguous")
    calls: list = []
    monkeypatch.setattr(uq, "record_miss", lambda key, raw=None: calls.append(key))

    out = resolver_mod.resolve("Zzqx Ambiguous Thing", None)
    assert out.status == "uncertain"
    assert calls == []


def test_resolver_db_error_is_not_enqueued(monkeypatch):
    _all_tiers_miss(monkeypatch)

    def _boom(*_a, **_k):
        raise ConnectionError("db down")

    monkeypatch.setattr(resolver_mod.db, "disambiguate", _boom)
    calls: list = []
    monkeypatch.setattr(uq, "record_miss", lambda key, raw=None: calls.append(key))

    out = resolver_mod.resolve("Zzqx Db Down Thing", None)
    assert out.status == "uncertain"
    assert calls == []


def test_one_shot_tier_walk_writes_nothing(monkeypatch):
    _all_tiers_miss(monkeypatch)
    calls: list = []
    monkeypatch.setattr(uq, "record_miss", lambda key, raw=None: calls.append(key))
    out = resolver_mod._resolve_uncached("zzqx walk", None, atom="zzqx walk")
    assert out.resolution_layer == "L5_unknown_queue"
    assert calls == []
