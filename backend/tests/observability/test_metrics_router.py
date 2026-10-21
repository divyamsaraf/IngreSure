from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.observability.metrics import record_request, reset_for_tests
from core.observability.miss_class_store import record_miss_class, reset_for_tests as reset_miss
from core.observability.router import router


def _client(monkeypatch, token="metrics-secret", miss_path=None):
    reset_for_tests()
    reset_miss(miss_path)
    if token is None:
        monkeypatch.delenv("METRICS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("METRICS_TOKEN", token)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_metrics_404_when_token_unset(monkeypatch, tmp_path):
    client = _client(monkeypatch, token=None, miss_path=tmp_path / "miss.json")
    res = client.get("/metrics")
    assert res.status_code == 404


def test_metrics_401_without_or_wrong_token(monkeypatch, tmp_path):
    client = _client(monkeypatch, miss_path=tmp_path / "miss.json")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_metrics_ok_with_bearer_or_header(monkeypatch, tmp_path):
    path = tmp_path / "miss.json"
    client = _client(monkeypatch, miss_path=path)
    record_request(route="/api/v1/evaluate-product", status=500, latency_ms=40, degraded=True)
    record_miss_class("M1_absent", normalized_key="zyzzx-not-stored", persist=True)

    bearer = client.get("/metrics", headers={"Authorization": "Bearer metrics-secret"})
    assert bearer.status_code == 200
    body = bearer.json()
    assert body["requests"]["status_5xx_total"] == 1
    assert body["requests"]["degraded_total"] == 1
    assert body["miss_class"]["by_class"]["M1_absent"]["count"] == 1
    assert "zyzzx" not in bearer.text
    assert body["alerts"]["degraded_rate_warn_above"] == 0.01
    assert body["alerts"]["status_5xx_rate_warn_above"] == 0.005

    header = client.get("/metrics", headers={"X-Metrics-Token": "metrics-secret"})
    assert header.status_code == 200
