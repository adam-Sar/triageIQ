"""Tool-level behavior: input validation and result formatting."""

import json

from agent.tools import check_service_health, get_recent_logs, inspect_endpoint
from main import build_incident_description
from tests.conftest import dump


def test_inspect_endpoint_rejects_external_paths():
    result = json.loads(inspect_endpoint.invoke({"path": "https://evil.example.com"}))
    assert "error" in result

    result = json.loads(inspect_endpoint.invoke({"path": "products"}))
    assert "error" in result


def test_inspect_endpoint_reports_status_and_latency(fake_transport):
    fake_transport({("GET", "/orders"): {"detail": "Service temporarily unavailable"}})
    result = json.loads(inspect_endpoint.invoke({"path": "/orders"}))
    assert result["http_status"] == 200
    assert result["response_time_ms"] == 42.0
    assert "unavailable" in result["body_excerpt"]


def test_get_recent_logs_normalizes_severity_and_limit(fake_transport, monkeypatch):
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(kwargs.get("params", {}))
        return 200, 1.0, {"logs": [], "total": 0}

    monkeypatch.setattr("agent.tools._request", fake_request)
    get_recent_logs.invoke({"severity": "error", "limit": 9999})
    assert captured["severity"] == "ERROR"
    assert captured["limit"] == 500


def test_health_tool_shapes_result(fake_transport):
    fake_transport({("GET", "/health"): {"status": "degraded", "dependencies": {"database": "unreachable"}}})
    result = json.loads(check_service_health.invoke({}))
    assert result["http_status"] == 200
    assert result["service_status"] == "degraded"
    assert result["dependencies"]["database"] == "unreachable"


def test_incident_description_reports_symptoms_not_scenario_names():
    degraded = build_incident_description({
        "total_requests": 140, "error_rate": 0.4, "avg_response_ms": 1860.0,
        "p95_response_ms": 4885.0, "window_minutes": 5,
    })
    assert "40%" in degraded
    assert "shop-backend" in degraded
    for leak in ("db_timeout", "database", "scenario", "auth", "healthy"):
        assert leak not in degraded.lower()

    normal = build_incident_description({
        "total_requests": 140, "error_rate": 0.01, "avg_response_ms": 120.0,
        "p95_response_ms": 210.0, "window_minutes": 5,
    })
    assert "mostly normal" in normal
