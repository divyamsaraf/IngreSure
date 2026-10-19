from core.knowledge.ike2.coverage_os.induction.cluster import load_clusters


def test_cluster_hybrid_frequency_and_miss_class():
    entries = {
        "beef brisket": {
            "normalized_key": "beef brisket",
            "raw_inputs": ["Beef brisket"],
            "frequency": 10,
        },
        "xyz junk": {
            "normalized_key": "xyz junk",
            "raw_inputs": ["xyz junk"],
            "frequency": 2,
        },
    }
    items = load_clusters(entries=entries, min_frequency=2)
    assert items[0].normalized_key == "beef brisket"
    assert items[0].frequency == 10
    assert items[0].miss_class.startswith("M2")
    assert items[1].miss_class  # classified, co-equal signal present
