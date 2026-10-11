"""FastAPI app simulating a small e-commerce backend service.

The service behaves according to the active scenario. Activating a scenario
generates a synthetic batch of request logs (written to stdout and a JSONL
file) and refreshes the metrics derived from them, so the dashboard and the
AI agent always see consistent data.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from simulator.scenarios import (
    SERVICE_NAME,
    SCENARIOS,
    Scenario,
    generate_records,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulator")

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "service.log"
_LOG_DIR.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_file_handler)
logger.propagate = False


class SimulatorState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.scenario: Scenario = SCENARIOS["healthy"]
        self.records: list[dict] = []
        self.activated_at: datetime = datetime.now(timezone.utc)
        self.reload_scenario(self.scenario)

    def reload_scenario(self, scenario: Scenario) -> None:
        records = generate_records(scenario)
        with self._lock:
            self.scenario = scenario
            self.records = records
            self.activated_at = datetime.now(timezone.utc)
        for record in records[-15:]:
            logger.info(json.dumps(record))

    def snapshot(self) -> tuple[Scenario, list[dict]]:
        with self._lock:
            return self.scenario, list(self.records)


state = SimulatorState()

app = FastAPI(title="Monitored Service Simulator", version="1.0.0")


def _metrics(records: list[dict], window_minutes: int = 5) -> dict[str, Any]:
    total = len(records)
    errors_4xx = sum(1 for r in records if 400 <= r["status_code"] < 500)
    errors_5xx = sum(1 for r in records if r["status_code"] >= 500)
    durations = sorted(r["duration_ms"] for r in records)
    p95_index = max(0, int(total * 0.95) - 1)
    avg_ms = sum(durations) / total if total else 0

    endpoint_stats: dict[str, dict[str, float]] = {}
    for r in records:
        if r["endpoint"] == "-":
            continue
        stats = endpoint_stats.setdefault(r["endpoint"], {"count": 0, "total_ms": 0, "errors": 0})
        stats["count"] += 1
        stats["total_ms"] += r["duration_ms"]
        stats["errors"] += 1 if r["status_code"] >= 400 else 0

    now = datetime.now(timezone.utc)
    buckets = 10
    bucket_seconds = window_minutes * 60 / buckets
    timeline = []
    for i in range(buckets):
        bucket_end = now - timedelta(seconds=(buckets - 1 - i) * bucket_seconds)
        bucket_start = bucket_end - timedelta(seconds=bucket_seconds)
        in_bucket = [
            r for r in records
            if bucket_start <= datetime.fromisoformat(r["timestamp"]) < bucket_end
        ]
        bucket_durations = [r["duration_ms"] for r in in_bucket]
        timeline.append({
            "label": bucket_end.strftime("%H:%M"),
            "requests": len(in_bucket),
            "avg_ms": round(sum(bucket_durations) / len(bucket_durations), 1) if bucket_durations else 0,
            "errors": sum(1 for r in in_bucket if r["status_code"] >= 400),
        })

    return {
        "service": SERVICE_NAME,
        "scenario": state.scenario.id,
        "window_minutes": window_minutes,
        "total_requests": total,
        "error_count": errors_4xx + errors_5xx,
        "error_rate": round((errors_4xx + errors_5xx) / total, 3) if total else 0,
        "avg_response_ms": round(avg_ms, 1),
        "p95_response_ms": round(durations[p95_index], 1) if durations else 0,
        "status_breakdown": {"2xx": total - errors_4xx - errors_5xx, "4xx": errors_4xx, "5xx": errors_5xx},
        "endpoints": [
            {
                "endpoint": endpoint,
                "count": int(s["count"]),
                "avg_ms": round(s["total_ms"] / s["count"], 1),
                "error_rate": round(s["errors"] / s["count"], 3),
            }
            for endpoint, s in sorted(endpoint_stats.items())
        ],
        "timeline": timeline,
    }


def _scenario_payload(scenario: Scenario) -> dict[str, str]:
    return {"id": scenario.id, "name": scenario.name, "description": scenario.description}


class ScenarioRequest(BaseModel):
    scenario_id: str


@app.get("/health")
def health() -> dict:
    _, records = state.snapshot()
    db_errors = sum(1 for r in records if "atabase" in r["message"] or "connection" in r["message"].lower())
    degraded = state.scenario.id == "db_timeout" and db_errors > 0
    return {
        "status": "degraded" if degraded else "ok",
        "service": SERVICE_NAME,
        "uptime_s": int((datetime.now(timezone.utc) - state.activated_at).total_seconds()),
        "dependencies": {"database": "unreachable" if degraded else "reachable"},
    }


@app.get("/products")
def products() -> dict:
    behavior = _live_behavior()
    if behavior["status"] != 200:
        _raise_http(behavior)
    return {"items": [{"id": i, "name": f"Product {i}", "price": round(4.5 + i * 1.3, 2)} for i in range(1, 9)]}


@app.get("/orders")
def orders() -> dict:
    behavior = _live_behavior()
    if behavior["status"] != 200:
        _raise_http(behavior)
    return {"orders": [{"id": 10001 + i, "status": "confirmed", "total": round(19.9 + i * 7, 2)} for i in range(4)]}


@app.post("/orders")
def create_order() -> dict:
    return orders()


def _live_behavior() -> dict:
    scenario_id = state.scenario.id
    if scenario_id == "db_timeout":
        time.sleep(1.5)
        return {"status": 503, "detail": "Service temporarily unavailable: database connection timeout"}
    if scenario_id == "high_latency":
        time.sleep(2.2)
        return {"status": 200}
    if scenario_id == "auth_failure":
        return {"status": 401, "detail": "Authentication required: invalid or expired token"}
    if scenario_id == "service_failure":
        return {"status": 500, "detail": "Internal server error while processing request"}
    return {"status": 200}


def _raise_http(behavior: dict) -> None:
    raise HTTPException(status_code=behavior["status"], detail=behavior.get("detail", "Request failed"))


@app.get("/metrics")
def metrics() -> dict:
    _, records = state.snapshot()
    return _metrics(records)


@app.get("/internal/scenarios")
def list_scenarios() -> dict:
    return {"scenarios": [_scenario_payload(s) for s in SCENARIOS.values()]}


@app.get("/internal/scenario")
def current_scenario() -> dict:
    scenario, _ = state.snapshot()
    return _scenario_payload(scenario)


@app.post("/internal/scenario")
def activate_scenario(payload: ScenarioRequest) -> dict:
    scenario = SCENARIOS.get(payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{payload.scenario_id}'")
    state.reload_scenario(scenario)
    _, records = state.snapshot()
    return {"activated": _scenario_payload(scenario), "metrics": _metrics(records)}


@app.get("/internal/logs")
def recent_logs(
    severity: Literal["INFO", "WARNING", "ERROR"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    _, records = state.snapshot()
    if severity:
        records = [r for r in records if r["level"] == severity]
    return {"logs": list(reversed(records[-limit:])), "total": len(records)}
