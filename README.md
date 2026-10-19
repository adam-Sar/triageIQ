# triageIQ — AI Incident Investigation Agent

An end-to-end agentic AI demo: a simulated e-commerce backend fails in realistic ways, and a
LangGraph agent powered by Google Gemini investigates the incident — choosing its own tools,
reading real logs and metrics over HTTP, and writing a structured incident report from the
evidence it collected.

The frontend dashboard shows the agent's actual tool calls as they happen, alongside live
service metrics and a terminal-style log viewer.

> Everything except Gemini is synthetic and local. No real database, no real infrastructure —
> just a simulated service, a real agent, and real reasoning.

## Demo flow

1. Open the dashboard.
2. Pick a scenario (e.g. **Database timeout**) and click **Simulate Incident** — the service
   generates a deterministic batch of logs, errors, and metrics for the last 5 minutes.
3. Click **Investigate with AI**.
4. Watch the agent work: health check → metrics → logs → finish. Every step shown is a tool
   call the agent really made.
5. Read the report: root cause, severity, evidence, recommended fixes, and a confidence
   estimate.

The agent is never told which scenario is active — it only receives symptom-based alert text
(e.g. "error rate is elevated at 40%") and has to figure out the cause from tool results.

## Architecture

```
┌──────────────┐   /api (polling)    ┌───────────────┐   HTTP tools    ┌────────────────┐
│   React UI   │ ──────────────────► │   FastAPI     │ ──────────────► │  Simulated     │
│  (Vite, 5173)│ ◄────────────────── │  backend:8000 │ ◄────────────── │  service:8001  │
└──────────────┘   JSON              └───────┬───────┘   JSONL logs    └────────────────┘
                                            │
                                    LangGraph agent
                                            │
                                     Google Gemini
                                   (tool calling + report)
```

- **Simulated service** (`backend/simulator`) — a small FastAPI app (`/health`, `/products`,
  `/orders`, `/metrics`) that behaves according to the active scenario. Activating a scenario
  generates ~140 internally consistent synthetic request logs (JSONL file + stdout) and
  refreshed metrics. Five scenarios: healthy, database timeout, high latency, auth failures,
  internal server errors.
- **Agent** (`backend/agent`) — a LangGraph state machine: `agent → tools → agent → … → report`.
  Gemini picks tools (`check_service_health`, `get_service_metrics`, `get_recent_logs`,
  `inspect_endpoint`, `finish_investigation`); every invocation and result is recorded for the
  UI. Hard limit of 5 tool steps, tool timeouts, and clear handling of missing keys / rate
  limits / invalid models.
- **Backend API** (`backend/main.py`) — scenario control, status/metrics/logs proxies, and
  investigation lifecycle (`POST /api/investigations` runs the graph in a background thread;
  the frontend polls `GET /api/investigations/{id}`).
- **Frontend** (`frontend`) — React + Vite + Tailwind CSS + Recharts + Lucide. Dark
  observability-style dashboard: overview stats and latency/error chart, scenario selector,
  log viewer, live investigation timeline, and report card.

## Project structure

```
incident-agent/
├── backend/
│   ├── agent/
│   │   ├── graph.py      # LangGraph workflow: nodes, edges, step limit, report
│   │   ├── tools.py      # LangChain tools (real HTTP calls to the simulator)
│   │   └── models.py     # IncidentReport / Investigation pydantic models
│   ├── simulator/
│   │   ├── scenarios.py  # Scenario definitions + seeded synthetic log generation
│   │   └── service.py    # Monitored FastAPI service (health, products, orders, metrics)
│   ├── main.py           # Backend API (scenarios, status, logs, investigations)
│   ├── config.py         # Environment settings
│   └── requirements.txt
├── frontend/
│   ├── src/components/   # Dashboard sections
│   ├── src/lib/api.ts    # API client
│   └── src/types.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

## Running locally (no Docker)

Requires Python 3.11+ and Node 18+.

```bash
# 1. Configure
cp .env.example .env          # then paste your Gemini API key into GOOGLE_API_KEY
```

Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
# 2. Backend
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt      # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt  # macOS/Linux

# terminal 1 — simulated service (port 8001)
uvicorn simulator.service:app --port 8001 --app-dir backend

# terminal 2 — API + agent (port 8000)
uvicorn main:app --port 8000 --app-dir backend

# 3. Frontend (port 5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Running with Docker

```bash
cp .env.example .env    # add your GOOGLE_API_KEY
docker compose up --build
```

Open http://localhost:3000. The dashboard, API, and simulator all run in containers; the
Gemini key is only ever read by the backend.

## Configuration

| Variable         | Default                  | Purpose                                    |
| ---------------- | ------------------------ | ------------------------------------------ |
| `GOOGLE_API_KEY` | — (required for the AI)  | Gemini API key, free tier works            |
| `GEMINI_MODEL`   | `gemini-3.5-flash-lite`  | Any Gemini model with tool calling         |
| `SIMULATOR_URL`  | `http://localhost:8001`  | Where the agent/API reach the simulator    |
| `MAX_TOOL_STEPS` | `5`                      | Hard cap on agent tool calls               |
| `TOOL_TIMEOUT_S` | `10`                     | Per-request timeout for tools              |

Without a valid `GOOGLE_API_KEY` the dashboard, scenarios, logs, and metrics all still work —
only the investigation fails, with a clear error message explaining why.

## What is simulated vs real

**Simulated:** the monitored service, its traffic, errors, latencies, logs, and metrics. All
data is generated locally with seeded randomness (deterministic per scenario). There is no
database, auth provider, or external system.

**Real:** the agent's tool calls (actual HTTP requests to the simulator), Gemini's tool
selection and reasoning, the LangGraph state machine, and the report generation. The
investigation timeline in the UI is a faithful record of what the agent actually did.

## Tests

```bash
.venv\Scripts\python -m pytest      # or: python -m pytest
```

Covers scenario generation characteristics, simulator endpoints, tool behavior, and the
LangGraph workflow (tool recording, step limits, error handling) using a scripted fake LLM —
no API calls needed.

## API reference (summary)

| Method | Path                              | Purpose                              |
| ------ | --------------------------------- | ------------------------------------ |
| GET    | `/api/status`                     | Health + active scenario + metrics   |
| GET    | `/api/scenarios`                  | Available failure scenarios          |
| POST   | `/api/scenarios/{id}/activate`    | Activate a scenario, regenerate data |
| GET    | `/api/logs?severity=&limit=`      | Recent log entries                   |
| POST   | `/api/investigations`             | Start an AI investigation            |
| GET    | `/api/investigations/{id}`        | Investigation progress/report        |
