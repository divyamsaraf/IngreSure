# backend/tests/ike2/coverage_os/test_adapt_role_passthrough.py
from core.knowledge.ike2.etl.adapt import map_record


def test_map_record_preserves_role():
    raw = {
        "canonical_name": "vinegar",
        "role": "culinary_keep",
        "plant_origin": True,
    }
    row, _aliases = map_record(raw, canonical_source="test", default_state="LOCKED")
    assert row.get("role") == "culinary_keep"
