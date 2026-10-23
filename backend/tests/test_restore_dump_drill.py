"""scripts/restore_dump_drill.py: checksum + row-count restore into throwaway local Postgres."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "restore_dump_drill.py"


def _load():
    spec = importlib.util.spec_from_file_location("restore_dump_drill", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_dump_path_is_the_local_backup():
    mod = _load()
    expected = (
        Path.home()
        / "Documents"
        / "IngreSure-backups"
        / "gcufjqokqqmcuuayaybu-full-role-postgres-20261022T2354Z.dump"
    )
    assert Path(mod.DEFAULT_DUMP) == expected


def test_docker_image_is_throwaway_pgvector_pg17():
    mod = _load()
    assert mod.DOCKER_IMAGE == "pgvector/pgvector:pg17"


def test_checksum_mismatch_is_nonzero(tmp_path):
    mod = _load()
    dump = tmp_path / "x.dump"
    dump.write_bytes(b"not-a-real-dump")
    actual = hashlib.sha256(dump.read_bytes()).hexdigest()
    wrong = "0" * 64
    assert actual != wrong
    with pytest.raises(mod.ChecksumMismatch):
        mod.verify_checksum(dump, wrong)


def test_checksum_match_passes(tmp_path):
    mod = _load()
    dump = tmp_path / "x.dump"
    dump.write_bytes(b"abc")
    expected = hashlib.sha256(b"abc").hexdigest()
    mod.verify_checksum(dump, expected)


def test_row_count_mismatch_lists_tables():
    mod = _load()
    actual = {"public.ike2_aliases": 10, "ike2_staging.stg_rejects": 0}
    expected = {"public.ike2_aliases": 9, "ike2_staging.stg_rejects": 0}
    mismatches = mod.compare_row_counts(actual, expected)
    assert mismatches
    assert any("ike2_aliases" in m for m in mismatches)


def test_row_count_match_is_empty():
    mod = _load()
    counts = {"public.users": 1, "ike2_staging.ingredient_groups": 2}
    assert mod.compare_row_counts(counts, counts) == []


def test_refuses_non_local_host():
    mod = _load()
    with pytest.raises(mod.RemoteHostForbidden):
        mod.assert_local_only("db.supabase.co")
    with pytest.raises(mod.RemoteHostForbidden):
        mod.assert_local_only("prod.example.com")
    mod.assert_local_only("127.0.0.1")
    mod.assert_local_only("localhost")


def test_main_checksum_mismatch_exits_nonzero_and_keeps_dump(tmp_path, monkeypatch):
    mod = _load()
    dump = tmp_path / "keep.dump"
    dump.write_bytes(b"payload")
    counts = tmp_path / "counts.json"
    counts.write_text(json.dumps({"public.t": 0}))
    checksum_file = tmp_path / "keep.dump.sha256"
    checksum_file.write_text("0" * 64)

    monkeypatch.setattr(mod, "run_isolated_restore", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not restore")))
    rc = mod.main(["--dump", str(dump), "--counts", str(counts), "--checksum-file", str(checksum_file)])
    assert rc != 0
    assert dump.exists()


def test_main_missing_dump_exits_nonzero_without_deleting(tmp_path):
    mod = _load()
    missing = tmp_path / "nope.dump"
    counts = tmp_path / "counts.json"
    counts.write_text("{}")
    rc = mod.main(["--dump", str(missing), "--counts", str(counts), "--checksum", "a" * 64])
    assert rc != 0
    assert not missing.exists()


def test_main_row_count_mismatch_exits_nonzero(tmp_path, monkeypatch):
    mod = _load()
    dump = tmp_path / "ok.dump"
    dump.write_bytes(b"payload")
    expected_hex = hashlib.sha256(b"payload").hexdigest()
    counts = tmp_path / "counts.json"
    counts.write_text(json.dumps({"public.ike2_aliases": 3}))

    monkeypatch.setattr(
        mod,
        "run_isolated_restore",
        lambda *a, **k: {"public.ike2_aliases": 1},
    )
    rc = mod.main(["--dump", str(dump), "--counts", str(counts), "--checksum", expected_hex])
    assert rc != 0
    assert dump.exists()


def test_isolated_restore_uses_pgvector_and_tears_down(monkeypatch, tmp_path):
    mod = _load()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setattr(mod, "_wait_for_postgres", lambda *a, **k: None)
    monkeypatch.setattr(mod, "_pg_restore", lambda *a, **k: None)
    monkeypatch.setattr(
        mod,
        "_count_tables",
        lambda *a, **k: {"public.ike2_aliases": 0, "ike2_staging.stg_rejects": 0},
    )

    dump = tmp_path / "x.dump"
    dump.write_bytes(b"x")
    out = mod.run_isolated_restore(dump)
    assert out["public.ike2_aliases"] == 0
    images = [c for c in calls if "pgvector/pgvector:pg17" in c]
    assert images, calls
    stops = [c for c in calls if c[:2] == ["docker", "rm"] or c[:3] == ["docker", "rm", "-f"] or (len(c) >= 2 and c[0] == "docker" and c[1] in {"rm", "stop"})]
    assert stops, calls
