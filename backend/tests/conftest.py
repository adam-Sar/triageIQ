"""Shared fixtures: a scripted fake LLM and a monkeypatched tool transport."""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent.models import IncidentReport


class ScriptedLLM(BaseChatModel):
    """Returns queued AIMessages in order; repeats the last one if run dry."""

    responses: list[BaseMessage] = []
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any) -> "ScriptedLLM":
        return self

    def with_structured_output(self, schema: Any) -> Any:
        report = IncidentReport(
            title="Scripted report",
            severity="high",
            affected_service="shop-backend",
            summary="Scripted summary",
            evidence=["scripted evidence"],
            root_cause="Scripted root cause",
            confidence=0.8,
            recommended_actions=["Do the scripted fix"],
        )

        class _Invoker:
            def invoke(self, _messages: Any) -> IncidentReport:
                return report

        return _Invoker()

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        message = self.responses[self.calls] if self.calls < len(self.responses) else self.responses[-1]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def tool_call(name: str, args: dict[str, Any] | None = None, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args or {}, "id": call_id}])


@pytest.fixture
def fake_transport(monkeypatch):
    """Patch the tools' HTTP helper so no real network is used in graph tests."""

    def patch(routes: dict[tuple[str, str], Any]):
        def fake_request(method: str, path: str, **kwargs: Any) -> tuple[int, float, Any]:
            body = routes.get((method, path), {})
            if callable(body):
                body = body()
            return 200, 42.0, body

        monkeypatch.setattr("agent.tools._request", fake_request)

    return patch


def dump(payload: Any) -> str:
    return json.dumps(payload)
