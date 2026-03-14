"""Evaluation runner (stub)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from coding_agent_ui.agent_core.agent import Agent
from coding_agent_ui.eval.rubrics import Rubric
from coding_agent_ui.eval.tasks import EvalTask


@dataclass(frozen=True)
class EvaluationResult:
    """Result of a single evaluation task."""

    task_id: str
    score: float
    notes: str


@dataclass(frozen=True)
class EvaluationReport:
    """Aggregate evaluation report."""

    results: List[EvaluationResult]


def run_evaluation(agent: Agent, tasks: List[EvalTask], rubric: Rubric) -> EvaluationReport:
    """Run the evaluation harness.

    Stub: this function should invoke the agent on each task and score the outputs
    using the rubric.
    """
    _ = (agent, tasks, rubric)
    raise NotImplementedError(
        "Evaluation harness is not implemented. Add scoring logic in run_evaluation()."
    )
