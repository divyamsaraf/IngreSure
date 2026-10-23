import json

from core.observability.miss_class_store import (
    hash_normalized_key,
    record_miss_class,
    reset_for_tests,
    snapshot_miss_classes,
)


def test_record_persists_counts_and_hashes_not_raw_keys(tmp_path):
    path = tmp_path / "miss_class.json"
    reset_for_tests(path)
    record_miss_class("M2_cut_part", normalized_key="beef brisket")
    record_miss_class("M2_cut_part", normalized_key="beef brisket")
    record_miss_class("M1_absent", normalized_key="camembert")

    snap = snapshot_miss_classes()
    assert snap["by_class"]["M2_cut_part"]["count"] == 2
    assert snap["by_class"]["M1_absent"]["count"] == 1
    assert snap["total"] == 3

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert "beef" not in raw.lower()
    assert "camembert" not in raw.lower()
    hashes = data["by_class"]["M2_cut_part"]["key_hashes"]
    assert hashes == [hash_normalized_key("beef brisket")]


def test_record_empty_tag_is_noop(tmp_path):
    reset_for_tests(tmp_path / "miss.json")
    record_miss_class("  ")
    assert snapshot_miss_classes()["total"] == 0
