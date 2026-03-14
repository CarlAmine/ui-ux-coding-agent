"""Benchmark task definitions for evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class EvalTask:
    """Single evaluation task."""

    task_id: str
    description: str
    input: Dict[str, Any]


DEFAULT_TASKS: List[EvalTask] = [
    EvalTask(
        task_id="frontend-layout-001",
        description="Fix broken mobile layout on a form page.",
        input={"task": "Fix broken mobile layout on the form page."},
    ),
    EvalTask(
        task_id="frontend-ux-002",
        description="Improve card grid spacing and typography.",
        input={"task": "Improve card grid spacing and typography."},
    ),
    EvalTask(
        task_id="frontend-states-003",
        description="Add loading, empty, and error states to a data table.",
        input={"task": "Add loading, empty, and error states to the data table."},
    ),
    EvalTask(
        task_id="frontend-a11y-004",
        description="Address missing labels and focus styles on a login form.",
        input={"task": "Fix accessibility issues on the login form (labels, focus styles)."},
    ),
    EvalTask(
        task_id="frontend-responsive-005",
        description="Improve navigation responsiveness for small screens.",
        input={"task": "Improve the navigation layout on small screens (320px)."},
    ),
]
