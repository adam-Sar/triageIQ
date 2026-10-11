"""LangChain tools the investigation agent can call.
Every tool talks to the simulated monitored service over HTTP and returns a
JSON string. Results are also parsed back into Python objects by the graph so
the frontend can display exactly what the agent observed.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
from langchain_core.tools import tool

from config import settings

_SAFE_PATH = re.compile(r"^/[A-Za-z0-9_\-/]*$")
_KNOWN_ENDPOINTS = "/health, /products, /orders, /metrics"


def _request(method: str, path: str, **kwargs: Any) -> tuple[int, float, Any]:
    url = f"{settings.simulator_url}{path}"
    timeout = kwargs.pop("timeout", settings.tool_timeout_s)
    start = time.perf_counter()
    response = requests.request(method, url, timeout=timeout, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text[:500]
    return response.status_code, elapsed_ms, body


def _json(payload: Any) -> str:
    return json.dumps(payload, default=str)


@tool
def check_service_health() -> str:
    """Check the overall health of the monitored service.

    Returns the HTTP status, response time in milliseconds, reported service
    status, and the state of its dependencies.
    """
    status, elapsed_ms, body = _request("GET", "/health")
    return _json({
        "http_status": status,
        "response_time_ms": round(elapsed_ms, 1),
        "available": 200 <= status < 300,
        "service_status": body.get("status") if isinstance(body, dict) else None,
        "dependencies": body.get("dependencies") if isinstance(body, dict) else None,
    })


@tool
def get_service_metrics() -> str:
    """Retrieve service metrics for the recent time window.

    Returns total requests, error count and rate, average and p95 response
    times, a status-code breakdown, per-endpoint statistics, and a per-bucket
    timeline of latency and errors.
    """
    status, elapsed_ms, body = _request("GET", "/metrics")
    if status != 200:
        return _json({"error": f"metrics endpoint returned HTTP {status}"})
    return _json(body)


@tool
def get_recent_logs(severity: str = "", limit: int = 50) -> str:
    """Retrieve recent application log entries from the monitored service.

    Args:
        severity: Optional filter: INFO, WARNING, or ERROR. Empty means all levels.
        limit: Maximum number of entries to return (1-500). Keep under 100 to save tokens.
    """
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 500))}
    if severity:
        params["severity"] = severity.upper()
    status, _, body = _request("GET", "/internal/logs", params=params)
    if status != 200:
        return _json({"error": f"log endpoint returned HTTP {status}"})
    logs = body.get("logs", [])
    return _json({
        "returned": len(logs),
        "total_matching": body.get("total", len(logs)),
        "logs": logs,
    })


@tool
def inspect_endpoint(path: str, method: str = "GET") -> str:
    """Send a request to a specific endpoint of the monitored service and
    report the HTTP status, latency, and a short body excerpt.

    Args:
        path: Relative path to test, e.g. /products or /orders.
            Known paths: /health, /products, /orders, /metrics.
        method: HTTP method to use, usually GET.
    """
    path = path.strip()
    if not _SAFE_PATH.match(path):
        return _json({"error": f"invalid path '{path}'. Use a relative service path like {_KNOWN_ENDPOINTS}."})
    try:
        status, elapsed_ms, body = _request(method.upper(), path)
    except requests.RequestException as exc:
        return _json({"path": path, "method": method.upper(), "error": f"request failed: {exc}"})
    body_text = body if isinstance(body, str) else _json(body)
    return _json({
        "path": path,
        "method": method.upper(),
        "http_status": status,
        "response_time_ms": round(elapsed_ms, 1),
        "body_excerpt": body_text[:400],
    })


@tool
def finish_investigation(summary: str) -> str:
    """Call this tool when enough evidence has been collected.

    Args:
        summary: One-sentence conclusion based on the evidence gathered so far.
    """
    return _json({"finished": True, "summary": summary})


INVESTIGATION_TOOLS = [
    check_service_health,
    get_service_metrics,
    get_recent_logs,
    inspect_endpoint,
    finish_investigation,
]
