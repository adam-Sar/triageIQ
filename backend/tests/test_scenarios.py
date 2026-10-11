"""Scenario generation behavior: consistency and scenario-specific signals."""

from simulator.scenarios import SCENARIOS, generate_records

REQUIRED_KEYS = {"timestamp", "level", "service", "endpoint", "method", "status_code", "duration_ms", "request_id", "message"}


def test_records_have_consistent_schema():
    for scenario in SCENARIOS.values():
        records = generate_records(scenario)
        assert len(records) >= 140
        for record in records:
            assert REQUIRED_KEYS.issubset(record)
            assert record["service"] == "shop-backend"
            assert record["level"] in {"INFO", "WARNING", "ERROR"}
            assert record["timestamp"] <= records[-1]["timestamp"]


def test_generation_is_reproducible():
    first = generate_records(SCENARIOS["db_timeout"])
    second = generate_records(SCENARIOS["db_timeout"])
    assert [r["message"] for r in first] == [r["message"] for r in second]
    assert [r["status_code"] for r in first] == [r["status_code"] for r in second]


def test_healthy_scenario_has_few_errors_and_low_latency():
    records = generate_records(SCENARIOS["healthy"])
    errors = [r for r in records if r["status_code"] >= 400]
    assert len(errors) <= 5
    assert all(r["duration_ms"] < 500 for r in records if r["status_code"] == 200)


def test_db_timeout_scenario_produces_timeout_evidence():
    records = generate_records(SCENARIOS["db_timeout"])
    timeout_errors = [r for r in records if r["status_code"] == 503]
    assert len(timeout_errors) > 30
    messages = " ".join(r["message"] for r in records)
    assert "timeout" in messages.lower()
    assert "connection pool exhausted" in messages.lower()
    assert all(r["duration_ms"] > 1500 for r in timeout_errors)


def test_high_latency_scenario_is_slow_but_successful():
    records = generate_records(SCENARIOS["high_latency"])
    slow = [r for r in records if r["duration_ms"] > 1500]
    assert len(slow) > 80
    assert all(r["status_code"] < 400 for r in slow)
    assert any("slow" in r["message"].lower() for r in records)


def test_auth_failure_scenario_produces_401s():
    records = generate_records(SCENARIOS["auth_failure"])
    unauthorized = [r for r in records if r["status_code"] == 401]
    assert 0.3 < len(unauthorized) / len(records) < 0.6
    assert any("auth" in r["message"].lower() for r in unauthorized)


def test_service_failure_scenario_produces_500s():
    records = generate_records(SCENARIOS["service_failure"])
    server_errors = [r for r in records if r["status_code"] == 500]
    assert 0.25 < len(server_errors) / len(records) < 0.6
    assert any("exception" in r["message"].lower() or "error" in r["message"].lower() for r in server_errors)
