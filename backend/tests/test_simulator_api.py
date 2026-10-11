"""Simulator HTTP surface: health, scenario activation, metrics, and logs."""

from fastapi.testclient import TestClient

from simulator.service import app

client = TestClient(app)


def test_health_is_ok_by_default():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["database"] == "reachable"


def test_unknown_scenario_returns_404():
    response = client.post("/internal/scenario", json={"scenario_id": "nope"})
    assert response.status_code == 404


def test_activating_db_timeout_updates_metrics_and_health():
    response = client.post("/internal/scenario", json={"scenario_id": "db_timeout"})
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["error_rate"] > 0.2
    assert metrics["status_breakdown"]["5xx"] > 20
    assert metrics["avg_response_ms"] > 500

    health = client.get("/health").json()
    assert health["status"] == "degraded"
    assert health["dependencies"]["database"] == "unreachable"


def test_scenario_error_rates_are_distinct():
    expectations = {
        "healthy": (0.0, 0.05),
        "auth_failure": (0.3, 0.6),
        "service_failure": (0.25, 0.6),
    }
    for scenario_id, (low, high) in expectations.items():
        body = client.post("/internal/scenario", json={"scenario_id": scenario_id}).json()
        assert low <= body["metrics"]["error_rate"] < high, scenario_id


def test_high_latency_is_slow_with_low_errors():
    body = client.post("/internal/scenario", json={"scenario_id": "high_latency"}).json()
    metrics = body["metrics"]
    assert metrics["avg_response_ms"] > 1000
    assert metrics["error_rate"] < 0.05


def test_log_filtering_by_severity():
    client.post("/internal/scenario", json={"scenario_id": "service_failure"})
    body = client.get("/internal/logs", params={"severity": "ERROR", "limit": 50}).json()
    assert body["logs"]
    assert all(log["level"] == "ERROR" for log in body["logs"])
    assert len(body["logs"]) <= 50


def test_logs_endpoint_returns_recent_entries():
    body = client.get("/internal/logs", params={"limit": 10}).json()
    assert len(body["logs"]) <= 10
    timestamps = [log["timestamp"] for log in body["logs"]]
    assert timestamps == sorted(timestamps, reverse=True)
