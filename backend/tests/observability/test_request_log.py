from core.observability.request_log import (
    build_log_record,
    encode_log_record,
    extract_observability_fields,
)


def test_extract_counts_status_not_ingredient_names():
    payload = {
        "schema_version": "ike2.v1",
        "verdict": {"status": "not_safe", "items": [{"name": "gelatin"}]},
        "ike2": {"schema_version": "ike2.v1", "external_verdict": "fail"},
    }
    fields = extract_observability_fields(payload)
    assert fields["engine"] == "ike2"
    assert fields["verdict_counts"]["not_safe"] == 1
    dumped = encode_log_record(fields)
    assert "gelatin" not in dumped


def test_extract_degraded_from_layer_only():
    fields = extract_observability_fields(
        {"resolution_layer": "L3_degraded", "canonical_name": "should-not-matter"}
    )
    assert fields["degraded"] is True
    record = build_log_record(
        request_id="r1",
        route="/api/v1/evaluate-product",
        method="POST",
        status=200,
        latency_ms=12,
        engine=fields["engine"],
        degraded=True,
        verdict_counts={},
    )
    line = encode_log_record(record)
    assert "should-not-matter" not in line
    assert '"degraded":true' in line
    assert '"request_id":"r1"' in line
