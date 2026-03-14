"""Base types for tool interfaces."""

from __future__ import annotations

from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel


class ToolError(RuntimeError):
    """Raised when a tool fails to execute properly."""


InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class BaseTool(Generic[InputModel, OutputModel]):
    """Base class for strongly-typed tools."""

    name: str
    description: str
    input_model: type[InputModel]
    output_model: type[OutputModel]

    def invoke(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input, run tool, and return raw output."""
        data = self.input_model.model_validate(raw_input)
        result = self.run(data)
        return result.model_dump()

    def run(self, data: InputModel) -> OutputModel:
        """Execute the tool.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Tool run() not implemented.")
