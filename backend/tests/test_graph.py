"""LangGraph workflow: tool execution, recording, limits, and routing."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.graph import (
    MAX_TOOL_STEPS,
    InvestigationState,
    build_graph,
    describe_llm_error,
    initial_messages,
    route_after_agent,
)
from agent.tools import get_service_metrics
from tests.conftest import ScriptedLLM, dump, tool_call

METRICS = {
    "service": "shop-backend",
    "total_requests": 140,
    "error_rate": 0.4,
    "avg_response_ms": 1800.0,
    "p95_response_ms": 4900.0,
    "status_breakdown": {"2xx": 84, "4xx": 0, "5xx": 56},
    "endpoints": [],
    "timeline": [],
    "window_minutes": 5,
}


def _state(llm: ScriptedLLM) -> InvestigationState:
    return {
        "messages": initial_messages("Automated alert for shop-backend."),
        "tool_records": [],
        "finished": False,
        "error": None,
        "report": None,
    }


def test_agent_records_real_tool_calls_and_finishes(fake_transport):
    fake_transport({("GET", "/metrics"): METRICS, ("GET", "/health"): {"status": "ok"}})
    llm = ScriptedLLM(responses=[
        tool_call("get_service_metrics", {"limit": 1}, "c1"),
        tool_call("finish_investigation", {"summary": "db pool exhausted"}, "c2"),
    ])
    graph = build_graph(llm)
    final = graph.invoke(_state(llm))

    assert [r["tool"] for r in final["tool_records"]] == ["get_service_metrics", "finish_investigation"]
    assert final["tool_records"][0]["step"] == 1
    assert final["tool_records"][0]["result"]["error_rate"] == 0.4
    assert "error rate" in final["tool_records"][0]["summary"].lower()
    assert final["finished"] is True
    assert final["report"]["title"] == "Scripted report"

    tool_messages = [m for m in final["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 2


def test_step_limit_stops_unbounded_loops(fake_transport):
    fake_transport({("GET", "/metrics"): METRICS})
    llm = ScriptedLLM(responses=[tool_call("get_service_metrics", {}, f"c{i}") for i in range(20)])
    graph = build_graph(llm)
    final = graph.invoke(_state(llm))

    assert len(final["tool_records"]) == MAX_TOOL_STEPS
    assert final["finished"] is False
    assert final["report"] is not None


def test_unknown_and_failing_tools_are_recorded_not_raised(fake_transport):
    fake_transport({})

    class ExplodingTool:
        name = "get_service_metrics"

        def invoke(self, _args):
            raise ConnectionError("simulator unreachable")

    import agent.graph as graph_module

    original = graph_module.INVESTIGATION_TOOLS
    graph_module.INVESTIGATION_TOOLS = [ExplodingTool()]
    try:
        llm = ScriptedLLM(responses=[
            tool_call("get_service_metrics", {}, "c1"),
            tool_call("finish_investigation", {"summary": "cannot reach simulator"}, "c2"),
        ])
        graph = build_graph(llm)
        final = graph.invoke(_state(llm))
    finally:
        graph_module.INVESTIGATION_TOOLS = original

    first = final["tool_records"][0]
    assert "failed" in first["summary"].lower()
    assert "simulator unreachable" in first["summary"]
    assert final["report"] is not None


def test_plain_answer_without_tool_call_goes_to_report(fake_transport):
    fake_transport({})
    llm = ScriptedLLM(responses=[AIMessage(content="I need no tools to answer this.")])
    graph = build_graph(llm)
    final = graph.invoke(_state(llm))

    assert final["tool_records"] == []
    assert final["report"] is not None


def test_route_after_agent():
    error_state = {"error": "boom", "messages": []}
    assert route_after_agent(error_state) == "report"

    plain = {"error": None, "messages": [AIMessage(content="done")]}
    assert route_after_agent(plain) == "report"

    calling = {"error": None, "messages": [tool_call("check_service_health", {}, "c1")]}
    assert route_after_agent(calling) == "tools"


def test_describe_llm_error_messages():
    assert "rate limit" in describe_llm_error(Exception("429 RESOURCE_EXHAUSTED: quota")).lower()
    assert "invalid" in describe_llm_error(Exception("API key not valid")).lower()
    assert "GEMINI_MODEL" in describe_llm_error(Exception("model not found"))
    assert "timed out" in describe_llm_error(Exception("request timed out")).lower()
