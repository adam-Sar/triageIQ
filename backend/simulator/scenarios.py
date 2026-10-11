"""Failure scenario definitions and synthetic request-log generation.

Each scenario produces an internally consistent set of request records over a
recent time window. Generation is seeded per scenario so activating the same
scenario twice yields the same observable behavior (timestamps shift relative
to activation time).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SERVICE_NAME = "shop-backend"

_WINDOW_MINUTES = 5
_REQUEST_COUNT = 140


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    seed: int


SCENARIOS: dict[str, Scenario] = {
    "healthy": Scenario(
        id="healthy",
        name="Healthy operation",
        description="Normal traffic with low latency and almost no errors.",
        seed=101,
    ),
    "db_timeout": Scenario(
        id="db_timeout",
        name="Database timeout",
        description="Database connections time out, causing HTTP 503 responses and pool exhaustion.",
        seed=202,
    ),
    "high_latency": Scenario(
        id="high_latency",
        name="High latency",
        description="Requests complete successfully but take several seconds; slow-query warnings appear.",
        seed=303,
    ),
    "auth_failure": Scenario(
        id="auth_failure",
        name="Authentication failures",
        description="A large share of requests are rejected with HTTP 401 and auth errors.",
        seed=404,
    ),
    "service_failure": Scenario(
        id="service_failure",
        name="Internal server errors",
        description="Unhandled exceptions inside request handlers produce HTTP 500 responses.",
        seed=505,
    ),
}

_LOG_TEMPLATES = {
    "products_ok": "Returned {n} products",
    "orders_ok": "Order {order} created for customer {cust}",
    "orders_listed": "Listed {n} recent orders",
}

_DB_TIMEOUT_MESSAGES = [
    "Database connection timeout after 5.0s",
    "psycopg2.OperationalError: connection timed out",
    "Could not acquire connection from pool within 5000ms",
    "Query cancelled: statement timeout exceeded",
]

_AUTH_MESSAGES = [
    "Authentication failed: token signature verification failed",
    "Expired JWT presented for protected endpoint",
    "Missing Authorization header",
    "Invalid API key supplied in request",
]

_SERVICE_FAILURE_MESSAGES = [
    "Unhandled exception in order processor: KeyError: 'inventory_count'",
    "ZeroDivisionError: division by zero in discount_calculator",
    "AttributeError: 'NoneType' object has no attribute 'id' while loading cart",
    "Internal error while serializing order response",
    "Uncaught exception in request handler: RuntimeError: cache closed",
]

_SLOW_QUERY_MESSAGES = [
    "Slow query: SELECT * FROM products WHERE category = 'all' ({s}s)",
    "Slow query: JOIN orders/customers took {s}s",
    "Slow query detected: fetch_recent_orders ({s}s, threshold 1.0s)",
]


def _request_id(rng: random.Random) -> str:
    return f"req-{rng.getrandbits(32):08x}"


def _record(
    ts: datetime,
    level: str,
    endpoint: str,
    method: str,
    status: int,
    duration_ms: float,
    request_id: str,
    message: str,
) -> dict:
    return {
        "timestamp": ts.isoformat(timespec="milliseconds"),
        "level": level,
        "service": SERVICE_NAME,
        "endpoint": endpoint,
        "method": method,
        "status_code": status,
        "duration_ms": round(duration_ms, 1),
        "request_id": request_id,
        "message": message,
    }


def _pick_endpoint(rng: random.Random) -> tuple[str, str]:
    if rng.random() < 0.55:
        return "/products", "GET"
    if rng.random() < 0.7:
        return "/orders", "POST"
    return "/orders", "GET"


def _spread(count: int, window: timedelta, rng: random.Random) -> list[datetime]:
    start = datetime.now(timezone.utc) - window
    return sorted(start + timedelta(seconds=rng.uniform(0, window.total_seconds())) for _ in range(count))


def _ok_message(rng: random.Random, endpoint: str) -> str:
    if endpoint == "/products":
        return _LOG_TEMPLATES["products_ok"].format(n=rng.randint(5, 40))
    if rng.random() < 0.6:
        return _LOG_TEMPLATES["orders_ok"].format(order=rng.randint(10000, 99999), cust=rng.randint(100, 999))
    return _LOG_TEMPLATES["orders_listed"].format(n=rng.randint(1, 25))


def _generate_healthy(rng: random.Random, count: int) -> list[dict]:
    records = []
    for ts in _spread(count, timedelta(minutes=_WINDOW_MINUTES), rng):
        endpoint, method = _pick_endpoint(rng)
        duration = rng.uniform(35, 210)
        if rng.random() < 0.01:
            records.append(_record(ts, "ERROR", endpoint, method, 500, rng.uniform(80, 400),
                                   _request_id(rng), "Unhandled exception while rendering response payload"))
        else:
            records.append(_record(ts, "INFO", endpoint, method, 200, duration,
                                   _request_id(rng), _ok_message(rng, endpoint)))
    return records


def _generate_db_timeout(rng: random.Random, count: int) -> list[dict]:
    records = []
    for ts in _spread(count, timedelta(minutes=_WINDOW_MINUTES), rng):
        endpoint, method = _pick_endpoint(rng)
        if rng.random() < 0.40:
            duration = rng.uniform(2000, 5200)
            message = rng.choice(_DB_TIMEOUT_MESSAGES)
            records.append(_record(ts, "ERROR", endpoint, method, 503, duration, _request_id(rng), message))
        else:
            duration = rng.uniform(250, 1100)
            if duration > 900:
                message = rng.choice(_SLOW_QUERY_MESSAGES).format(s=round(duration / 1000, 1))
                level = "WARNING"
            else:
                message, level = _ok_message(rng, endpoint), "INFO"
            records.append(_record(ts, level, endpoint, method, 200, duration, _request_id(rng), message))

    for _ in range(4):
        ts = _spread(1, timedelta(minutes=_WINDOW_MINUTES), rng)[0]
        records.append(_record(ts, "ERROR", "-", "-", 0, 0, _request_id(rng),
                               "Connection pool exhausted: 10/10 connections in use"))
    for _ in range(3):
        ts = _spread(1, timedelta(minutes=_WINDOW_MINUTES), rng)[0]
        records.append(_record(ts, "WARNING", "-", "-", 0, 0, _request_id(rng),
                               "Retrying database operation (attempt 2/3) after connection failure"))
    records.sort(key=lambda r: r["timestamp"])
    return records


def _generate_high_latency(rng: random.Random, count: int) -> list[dict]:
    records = []
    for ts in _spread(count, timedelta(minutes=_WINDOW_MINUTES), rng):
        endpoint, method = _pick_endpoint(rng)
        if rng.random() < 0.85:
            duration = rng.uniform(1800, 5800)
            level = "WARNING"
            status = 200
            message = f"Slow request: {method} {endpoint} completed in {duration / 1000:.1f}s"
        else:
            duration = rng.uniform(40, 200)
            level, status = "INFO", 200
            message = _ok_message(rng, endpoint)
        records.append(_record(ts, level, endpoint, method, status, duration, _request_id(rng), message))

    for _ in range(5):
        ts = _spread(1, timedelta(minutes=_WINDOW_MINUTES), rng)[0]
        records.append(_record(ts, "WARNING", "-", "-", 0, 0, _request_id(rng),
                               rng.choice(_SLOW_QUERY_MESSAGES).format(s=round(rng.uniform(2.0, 5.5), 1))))
    records.sort(key=lambda r: r["timestamp"])
    return records


def _generate_auth_failure(rng: random.Random, count: int) -> list[dict]:
    records = []
    for ts in _spread(count, timedelta(minutes=_WINDOW_MINUTES), rng):
        endpoint, method = _pick_endpoint(rng)
        if rng.random() < 0.45:
            level = "ERROR" if rng.random() < 0.6 else "WARNING"
            message = rng.choice(_AUTH_MESSAGES)
            records.append(_record(ts, level, endpoint, method, 401, rng.uniform(15, 90),
                                   _request_id(rng), message))
        else:
            records.append(_record(ts, "INFO", endpoint, method, 200, rng.uniform(30, 180),
                                   _request_id(rng), _ok_message(rng, endpoint)))
    return records


def _generate_service_failure(rng: random.Random, count: int) -> list[dict]:
    records = []
    for ts in _spread(count, timedelta(minutes=_WINDOW_MINUTES), rng):
        endpoint, method = _pick_endpoint(rng)
        roll = rng.random()
        if roll < 0.35:
            records.append(_record(ts, "ERROR", endpoint, method, 500, rng.uniform(60, 500),
                                   _request_id(rng), rng.choice(_SERVICE_FAILURE_MESSAGES)))
        elif roll < 0.45:
            records.append(_record(ts, "WARNING", endpoint, method, 500, rng.uniform(60, 400),
                                   _request_id(rng), "Request failed, retrying (attempt 2/3)"))
        else:
            records.append(_record(ts, "INFO", endpoint, method, 200, rng.uniform(35, 220),
                                   _request_id(rng), _ok_message(rng, endpoint)))
    return records


_GENERATORS: dict[str, Callable[[random.Random, int], list[dict]]] = {
    "healthy": _generate_healthy,
    "db_timeout": _generate_db_timeout,
    "high_latency": _generate_high_latency,
    "auth_failure": _generate_auth_failure,
    "service_failure": _generate_service_failure,
}


def generate_records(scenario: Scenario, count: int = _REQUEST_COUNT) -> list[dict]:
    rng = random.Random(scenario.seed)
    records = _GENERATORS[scenario.id](rng, count)
    records.sort(key=lambda r: r["timestamp"])
    return records
