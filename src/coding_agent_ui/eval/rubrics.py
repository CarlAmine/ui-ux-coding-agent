"""Rubrics for evaluation scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RubricItem:
    """Single rubric item with a description and max score."""

    name: str
    description: str
    max_score: int = 5


@dataclass(frozen=True)
class Rubric:
    """Collection of rubric items."""

    items: List[RubricItem]


DEFAULT_RUBRIC = Rubric(
    items=[
        RubricItem(
            name="hierarchy",
            description="Improves visual hierarchy and information structure.",
        ),
        RubricItem(
            name="spacing",
            description="Improves spacing consistency and layout alignment.",
        ),
        RubricItem(
            name="accessibility",
            description="Addresses accessibility issues (contrast, focus, labels).",
        ),
        RubricItem(
            name="responsiveness",
            description="Preserves or improves responsive behavior.",
        ),
        RubricItem(
            name="states",
            description="Handles loading, empty, and error states gracefully.",
        ),
        RubricItem(
            name="design_system",
            description="Uses existing design-system tokens/components.",
        ),
        RubricItem(
            name="usability",
            description="Improves clarity and ease of use without visual churn.",
        ),
    ]
)
