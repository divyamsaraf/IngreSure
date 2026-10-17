"""Item 4 Prompt 3: L3 mirror must remain a documented no-op."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from core.knowledge.ike2.coverage_os.promote_writer import mirror_l3_inject


def test_mirror_l3_inject_writes_nothing(tmp_path, caplog):
    marker = tmp_path / "should_not_appear.json"
    entry = {"candidate_key": "alias:test|canon:test", "payload": {"write_kind": "variant_alias"}}

    with caplog.at_level(logging.INFO):
        with patch("core.knowledge.ike2.coverage_os.promote_writer._atomic_write_json") as write_json:
            with patch("core.knowledge.ike2.coverage_os.promote_writer._read_json") as read_json:
                mirror_l3_inject(entry)
                write_json.assert_not_called()
                read_json.assert_not_called()

    assert not marker.exists()
    assert list(tmp_path.iterdir()) == []
    assert any("L3 mirror" in r.message for r in caplog.records)
