"""LangGraph workflow for AI incident investigation.

Flow: agent (Gemini picks a tool) -> tools (real HTTP calls to the simulator)
-> agent ... until the agent finishes or the step limit is reached -> a final
structured report. Every executed tool call is recorded so the frontend can
show what the agent actually did.
"""

from __future__ import annotations

import json
import operator
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent.models import IncidentReport
from agent.tools import INVESTIGATION_TOOLS
from config import settings

MAX_TOOL_STEPS = settings.max_tool_steps

_SYSTEM_PROMPT = """You are an incident response investigator for the "shop-backend" service, \
a small e-commerce API exposing /health, /products, /orders and /metrics.

You are given an alert description. Investigate it by calling tools, one step at a time:

1. Start broad: check service health and fetch service metrics to see the overall picture.
2. Then drill down: pull recent logs (optionally filtered by severity) and inspect specific \
endpoints that look affected.
3. Compare evidence: error messages, status codes, response times, and which endpoints fail.

Guidelines:
- Call exactly one tool per turn unless the same evidence clearly serves multiple questions.
- You have at most {max_steps} tool calls, so make each one count.
- When you have enough evidence to explain the situation, call finish_investigation.
- Base every conclusion only on evidence returned by tools. Never invent log entries or metrics.
"""


class InvestigationState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_records: Annotated[list[dict[str, Any]], operator.add]
    finished: bool
    error: str | None
    report: dict[str, Any] | None


def describe_llm_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "429" in text or "resource_exhausted" in lowered or "quota" in lowered:
        return ("Gemini API rate limit or quota exceeded. Wait a minute and try again, "
                "or check your plan at https://ai.google.dev/pricing")
    if "api key" in lowered and ("invalid" in lowered or "expired" in lowered or "not valid" in lowered):
        return "The GOOGLE_API_KEY appears to be invalid or expired. Check the value in your .env file."
    if "not found" in lowered or "no longer available" in lowered:
        return (f"Model '{settings.gemini_model}' is not available for this API key. "
                "Set GEMINI_MODEL in .env to a model your account can use, e.g. gemini-3.5-flash-lite.")
    if "timed out" in lowered or "timeout" in lowered:
        return "The Gemini API request timed out. Try again in a moment."
    return f"Gemini API call failed: {text[:300]}"


def create_investigator_llm() -> ChatGoogleGenerativeAI:
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. Add it to the .env file in the project root "
            "(see .env.example), then restart the API."
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def summarize_result(tool_name: str, arguments: dict[str, Any], result: dict[str, Any]) -> str:
    """Build a short human-readable line from the actual tool result."""
    if tool_name == "finish_investigation":
        return f"Investigation complete: {result.get('summary', '')}"
    if "error" in result:
        return f"{tool_name} failed: {result['error']}"

    if tool_name == "check_service_health":
        return (f"Health check: HTTP {result.get('http_status')} in {result.get('response_time_ms')}ms "
                f"— service reports '{result.get('service_status')}'")
    if tool_name == "get_service_metrics":
        rate = result.get("error_rate", 0)
        return (f"Metrics: {result.get('total_requests')} requests, "
                f"{rate * 100:.1f}% error rate, avg {result.get('avg_response_ms')}ms")
    if tool_name == "get_recent_logs":
        logs = result.get("logs", [])
        total = result.get("total_matching", len(logs))
        top = logs[0]["message"] if logs else "no entries"
        return f"Retrieved {len(logs)} of {total} matching logs. Most recent: \"{top}\""
    if tool_name == "inspect_endpoint":
        return (f"{result.get('method')} {result.get('path')} returned HTTP {result.get('http_status')} "
                f"in {result.get('response_time_ms')}ms")
    return json.dumps(result)[:120]


def _result_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        return {"raw": str(content)[:300]}


def select_tool(state: InvestigationState, llm: ChatGoogleGenerativeAI) -> dict[str, Any]:
    try:
        ai_msg = llm.bind_tools(INVESTIGATION_TOOLS).invoke(state["messages"])
        return {"messages": [ai_msg], "error": None}
    except Exception as exc:  # noqa: BLE001 - any LLM failure ends the run with a clear message
        return {"error": describe_llm_error(exc)}


def run_tools(state: InvestigationState) -> dict[str, Any]:
    ai_msg: AIMessage = state["messages"][-1]
    step_base = len(state["tool_records"])
    records: list[dict[str, Any]] = []
    tool_messages: list[ToolMessage] = []
    finished = False

    for offset, call in enumerate(ai_msg.tool_calls):
        tool_name = call["name"]
        arguments = call.get("args") or {}
        tool_impl = next((t for t in INVESTIGATION_TOOLS if t.name == tool_name), None)
        if tool_impl is None:
            content = _json_error(f"unknown tool '{tool_name}'")
        else:
            try:
                content = tool_impl.invoke(arguments)
            except Exception as exc:  # noqa: BLE001 - a failed tool is evidence, not a crash
                content = _json_error(f"{type(exc).__name__}: {exc}")

        result = _result_payload(content)
        if tool_name == "finish_investigation":
            finished = True

        records.append({
            "step": step_base + offset + 1,
            "tool": tool_name,
            "arguments": arguments,
            "summary": summarize_result(tool_name, arguments, result),
            "result": result,
            "timestamp": _now(),
        })
        tool_messages.append(ToolMessage(content=content, tool_call_id=call["id"]))

    return {"messages": tool_messages, "tool_records": records, "finished": finished}


def build_report(state: InvestigationState, llm: ChatGoogleGenerativeAI) -> dict[str, Any]:
    if state.get("error"):
        return {"report": None}
    instruction = HumanMessage(content=(
        "Based only on the evidence above, produce the final incident report. "
        "If the evidence shows the service is operating normally, set severity to 'healthy' "
        "and explain that no incident was found. Confidence is an estimate between 0 and 1."
    ))
    try:
        report = llm.with_structured_output(IncidentReport).invoke(
            [*state["messages"], instruction]
        )
        return {"report": report.model_dump()}
    except Exception as exc:  # noqa: BLE001
        return {"error": describe_llm_error(exc)}


def _json_error(message: str) -> str:
    return json.dumps({"error": message})


def route_after_agent(state: InvestigationState) -> str:
    if state.get("error"):
        return "report"
    last: AIMessage = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return "report"
    return "tools"


def route_after_tools(state: InvestigationState) -> str:
    if state.get("finished") or len(state["tool_records"]) >= MAX_TOOL_STEPS:
        return "report"
    return "agent"


def build_graph(llm: ChatGoogleGenerativeAI):
    graph = StateGraph(InvestigationState)

    graph.add_node("agent", lambda state: select_tool(state, llm))
    graph.add_node("tools", run_tools)
    graph.add_node("report", lambda state: build_report(state, llm))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "report": "report"})
    graph.add_conditional_edges("tools", route_after_tools, {"agent": "agent", "report": "report"})
    graph.add_edge("report", END)
    return graph.compile()


def initial_messages(incident_description: str) -> list[AnyMessage]:
    return [
        SystemMessage(content=_SYSTEM_PROMPT.format(max_steps=MAX_TOOL_STEPS)),
        HumanMessage(content=incident_description),
    ]
