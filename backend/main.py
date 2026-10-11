"""Backend API connecting the dashboard frontend to the simulator and the agent."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone

import requests as http
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.graph import build_graph, create_investigator_llm, initial_messages
from agent.models import IncidentReport, Investigation, InvestigationStep
from config import settings

app = FastAPI(title="AI Incident Investigation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_investigations: dict[str, Investigation] = {}
_lock = threading.Lock()


def _sim_request(method: str, path: str, **kwargs) -> dict:
    try:
        response = http.request(method, f"{settings.simulator_url}{path}", timeout=settings.tool_timeout_s, **kwargs)
    except http.RequestException:
        raise HTTPException(status_code=502, detail="Simulated service is unreachable. Is it running?")
    if response.status_code >= 400:
        detail = response.json().get("detail", f"simulator returned HTTP {response.status_code}")
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


class InvestigationRequest(BaseModel):
    description: str | None = None


class InvestigationSummary(BaseModel):
    id: str
    status: str
    description: str
    created_at: str


def build_incident_description(metrics: dict) -> str:
    """Describe symptoms only - never the scenario name, so the agent has to
    derive the root cause from evidence instead of reading the answer."""
    total = metrics["total_requests"]
    error_rate = metrics["error_rate"]
    avg_ms = metrics["avg_response_ms"]
    p95_ms = metrics["p95_response_ms"]

    parts = [f"Automated monitoring alert for the 'shop-backend' service "
             f"({total} requests over the last {metrics['window_minutes']} minutes)."]
    symptoms = []
    if error_rate >= 0.15:
        symptoms.append(f"the error rate is elevated at {error_rate * 100:.0f}%")
    elif error_rate >= 0.05:
        symptoms.append(f"the error rate is {error_rate * 100:.1f}%")
    if avg_ms >= 800:
        symptoms.append(f"average response time is {avg_ms:.0f}ms (p95 {p95_ms:.0f}ms)")
    elif p95_ms >= 2000:
        symptoms.append(f"p95 response time is {p95_ms:.0f}ms")
    if symptoms:
        parts.append("Monitoring observed that " + " and ".join(symptoms) + ".")
    else:
        parts.append("A low-priority anomaly alert fired, although aggregate metrics look mostly normal.")
    parts.append("Investigate the service, determine the most probable root cause, and report your findings.")
    return " ".join(parts)


@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def list_scenarios() -> dict:
    return _sim_request("GET", "/internal/scenarios")


@app.post("/api/scenarios/{scenario_id}/activate")
def activate_scenario(scenario_id: str) -> dict:
    result = _sim_request("POST", "/internal/scenario", json={"scenario_id": scenario_id})
    return {"scenario": result["activated"], "metrics": result["metrics"]}


@app.get("/api/status")
def service_status() -> dict:
    start = time.perf_counter()
    health = _sim_request("GET", "/health")
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    return {
        "health": health,
        "health_response_time_ms": latency_ms,
        "scenario": _sim_request("GET", "/internal/scenario"),
        "metrics": _sim_request("GET", "/metrics"),
    }


@app.get("/api/logs")
def recent_logs(severity: str | None = None, limit: int = 150) -> dict:
    params = {"limit": max(1, min(limit, 500))}
    if severity:
        params["severity"] = severity
    return _sim_request("GET", "/internal/logs", params=params)


@app.post("/api/investigations")
def start_investigation(payload: InvestigationRequest) -> Investigation:
    status = service_status()
    description = payload.description or build_incident_description(status["metrics"])

    investigation = Investigation(
        id=uuid.uuid4().hex[:12],
        status="pending",
        description=description,
        scenario=status["scenario"],
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with _lock:
        _investigations[investigation.id] = investigation

    threading.Thread(target=_execute_investigation, args=(investigation.id, description), daemon=True).start()
    return investigation


@app.get("/api/investigations")
def list_investigations() -> list[InvestigationSummary]:
    with _lock:
        items = sorted(_investigations.values(), key=lambda i: i.created_at, reverse=True)
        return [InvestigationSummary(**i.model_dump(include={"id", "status", "description", "created_at"}))
                for i in items]


@app.get("/api/investigations/{investigation_id}")
def get_investigation(investigation_id: str) -> Investigation:
    with _lock:
        investigation = _investigations.get(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


def _execute_investigation(investigation_id: str, description: str) -> None:
    with _lock:
        investigation = _investigations[investigation_id]
        investigation.status = "running"
    try:
        llm = create_investigator_llm()
        graph = build_graph(llm)
        state = {
            "messages": initial_messages(description),
            "tool_records": [],
            "finished": False,
            "error": None,
            "report": None,
        }
        for chunk in graph.stream(state, stream_mode="updates"):
            with _lock:
                for delta in chunk.values():
                    for record in delta.get("tool_records") or []:
                        investigation.steps.append(InvestigationStep(**record))
                    if delta.get("report"):
                        investigation.report = IncidentReport(**delta["report"])
                    if delta.get("error"):
                        investigation.error = delta["error"]
    except Exception as exc:  # noqa: BLE001 - surface any failure to the frontend
        with _lock:
            investigation.error = str(exc)[:400]
    finally:
        with _lock:
            investigation.status = "failed" if investigation.error else "completed"
            investigation.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
