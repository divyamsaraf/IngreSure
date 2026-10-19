"""Item 4.1 Prompt 2: decay policy module + L2 scope contract."""
from pathlib import Path

from core.knowledge.ike2 import decay


def test_decay_ttl_constants():
    assert decay.TTL_VERIFIED_DAYS == 180
    assert decay.TTL_AUTO_CLASSIFIED_DAYS == 90
    assert decay.DECAY_POLICY["VERIFIED"] == 180
    assert decay.DECAY_POLICY["AUTO_CLASSIFIED"] == 90
    assert "LOCKED" not in decay.DECAY_POLICY


def test_decay_module_documents_l2_out_of_scope():
    text = Path(decay.__file__).read_text(encoding="utf-8")
    assert "Coverage OS" in text
    assert "out of scope" in text.lower() or "intentionally out of scope" in text
    assert "auto=False" in text or "human-approved" in text
    assert "trust_refreshed_at" in text
