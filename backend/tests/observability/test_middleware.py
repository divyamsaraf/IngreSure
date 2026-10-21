import json
import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from core.observability.metrics import reset_for_tests, snapshot
from core.observability.middleware import StructuredRequestLogMiddleware
from core.observability.request_context import bind_request_observability


def _app():
    reset_for_tests()
    app = FastAPI()
    app.add_middleware(StructuredRequestLogMiddleware)

    @app.post("/api/v1/evaluate-product")
    def evaluate():
        return {
            "verdict": {"status": "safe"},
            "ike2": {"schema_version": "ike2.v1", "external_verdict": "pass"},
        }

    @app.post("/chat/grocery")
    def chat(request: Request):
        bind_request_observability(
            request, engine="ike2", degraded=True, verdict_counts={"uncertain": 1}
        )
        return {"ok": True, "query": "this must not appear in logs"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def test_middleware_logs_structured_fields_without_user_text(caplog):
    client = TestClient(_app())
    with caplog.at_level(logging.INFO, logger="ingresure.request"):
        res = client.post(
            "/chat/grocery",
            json={"query": "does this have milk?", "userProfile": {"allergens": ["Milk"]}},
            headers={"X-Request-ID": "req-fixed-1"},
        )
    assert res.status_code == 200
    assert res.headers["x-request-id"] == "req-fixed-1"
    lines = [r.getMessage() for r in caplog.records if r.name == "ingresure.request"]
    assert lines
    record = json.loads(lines[-1])
    assert record["request_id"] == "req-fixed-1"
    assert record["route"] == "/chat/grocery"
    assert record["status"] == 200
    assert record["engine"] == "ike2"
    assert record["degraded"] is True
    assert record["verdict_counts"]["uncertain"] == 1
    blob = json.dumps(record)
    assert "milk" not in blob.lower()
    assert "allergens" not in blob
    snap = snapshot()
    assert snap["requests_total"] == 1
    assert snap["degraded_total"] == 1


def test_middleware_reads_json_verdict_counts_only():
    client = TestClient(_app())
    res = client.post("/api/v1/evaluate-product", json={"ingredients_text": "water"})
    assert res.status_code == 200
    snap = snapshot()
    assert snap["requests_total"] == 1
    assert snap["degraded_total"] == 0
