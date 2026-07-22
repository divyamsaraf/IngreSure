import logging
from core.knowledge.ike2.coverage_os.auto_lane_guards import (
    select_sample_audit,
    check_volume_spike,
    log_volume_spike_if_needed,
)


def test_sample_audit_returns_non_empty_on_fixture_batch():
    batch = [{"id": i, "auto": True} for i in range(25)]
    sample = select_sample_audit(batch, every_n=10)
    assert sample  # non-empty
    assert len(sample) >= 2


def test_volume_spike_stub_logs(caplog):
    now = 1_000_000.0
    promos = [{"ts": now - 10, "source": "usda"} for _ in range(20)]
    assert check_volume_spike(promos, window_seconds=60, threshold=5, now=now) is True
    with caplog.at_level(logging.WARNING):
        log_volume_spike_if_needed(promos, window_seconds=60, threshold=5, now=now)
    assert any("volume spike" in r.message.lower() for r in caplog.records)
