"""Structured output schemas for the base agent."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ExecutionStatus = Literal["dry_run", "applied", "rolled_back", "no_changes"]


class TaskAnalysis(BaseModel):
    """Analysis of the user's task and constraints."""

    intent: str
    constraints: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class ImplementationStep(BaseModel):
    """Single step in an implementation plan."""

    title: str
    details: str
    files: List[str] = Field(default_factory=list)


class ImplementationPlan(BaseModel):
    """Ordered implementation plan."""

    steps: List[ImplementationStep]


class FileEdit(BaseModel):
    """Proposed edit for a single file."""

    path: str
    content: str
    change_summary: str
    rationale: str


class FileChange(BaseModel):
    """Summary of an applied or proposed change."""

    path: str
    change_summary: str
    rationale: str
    diff: Optional[str] = None


class ValidationRun(BaseModel):
    """Single validation command result."""

    name: str
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    artifacts: List[str] = Field(default_factory=list)


class ValidationResults(BaseModel):
    """Results from tests, linting, or manual checks."""

    runs: List[ValidationRun] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Structured result for the analysis step."""

    task_analysis: TaskAnalysis
    search_queries: List[str] = Field(default_factory=list)
    focus_files: List[str] = Field(default_factory=list)


class PlanResult(BaseModel):
    """Structured result for the planning step."""

    implementation_plan: ImplementationPlan
    target_files: List[str] = Field(default_factory=list)


class EditResult(BaseModel):
    """Structured result for the editing step."""

    edits: List[FileEdit] = Field(default_factory=list)


class AgentReport(BaseModel):
    """Top-level structured output from the agent."""

    execution_status: ExecutionStatus
    task_analysis: TaskAnalysis
    implementation_plan: ImplementationPlan
    attempted_changes: List[FileChange] = Field(default_factory=list)
    persisted_changes: List[FileChange] = Field(default_factory=list)
    validation_results: ValidationResults = Field(default_factory=ValidationResults)
    final_summary: str
    unresolved_risks: List[str] = Field(default_factory=list)
