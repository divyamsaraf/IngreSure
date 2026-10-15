"""Item 1 Prompt 7: legacy ingest deprecation hygiene."""
from __future__ import annotations

import warnings
from pathlib import Path

import scripts.ingest_layer1_json as ingest_mod


def test_ingest_layer1_main_emits_deprecation_warning(monkeypatch, capsys, tmp_path):
    """Calling main always warns before any DB work (empty file short-circuits)."""
    dump = tmp_path / "empty.json"
    dump.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(ingest_mod.sys, "argv", ["ingest_layer1_json.py", str(dump)])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            ingest_mod.main()
        except SystemExit as e:
            assert e.code == 0

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert any("bulk_inject" in str(w.message) for w in caught)
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "bulk_inject" in err


def test_data_readme_declares_bulk_inject_canonical():
    readme = Path(__file__).resolve().parents[3] / "data" / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "bulk_inject" in text
    assert "deprecated" in text.lower() or "DEPRECATED" in text
    assert "ingest_layer1_json" in text
