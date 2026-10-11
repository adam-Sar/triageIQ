"""Data models for investigations and incident reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["healthy", "low", "medium", "high", "critical"]


class IncidentReport(BaseModel):
    """Structured output produced by the agent after evidence collection."""

    title: str = Field(description="Short descriptive incident title")
    severity: Severity = Field(description="Incident severity; use 'healthy' when no real incident is found")
    affected_service: str = Field(description="Service or endpoint most affected")
    summary: str = Field(description="Plain-language summary of what happened")
    evidence: list[str] = Field(description="Concrete observations from the investigation tools")
    root_cause: str = Field(description="Most probable root cause based on the evidence")
    confidence: float = Field(ge=0.0, le=1.0, description="Estimate of confidence in the root cause")
    recommended_actions: list[str] = Field(description="Suggested remediation steps")


class InvestigationStep(BaseModel):
    """A single real action taken by the agent, shown in the frontend timeline."""

    step: int
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    summary: str
    result: Any = None
    timestamp: str


class Investigation(BaseModel):
    id: str
    status: Literal["pending", "running", "completed", "failed"]
    description: str
    scenario: dict[str, Any]
    steps: list[InvestigationStep] = Field(default_factory=list)
    report: IncidentReport | None = None
    error: str | None = None
    created_at: str
    finished_at: str | None = None
