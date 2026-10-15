import pytest


@pytest.fixture(autouse=True)
def _no_live_unknown_queue_writes(monkeypatch):
    """Resolver L5 misses must never write test artifacts into a real
    ``ike2_unknown_queue`` (tests/ike2 loads backend/.env). Tests that
    exercise the queue pass an explicit fake client instead."""
    from core.knowledge.ike2 import unknown_queue

    monkeypatch.setattr(unknown_queue, "_default_client", lambda: None)
