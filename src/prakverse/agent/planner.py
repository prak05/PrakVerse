from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ActionStep:
    """One named tool invocation in a plan."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    retries: int = 0


@dataclass(frozen=True)
class TaskPlan:
    """A visible, bounded sequence of local actions."""

    goal: str
    steps: tuple[ActionStep, ...]
    max_actions: int = 20

    def summary(self) -> list[str]:
        return [
            f"{index}. {step.description or step.tool}"
            for index, step in enumerate(self.steps, start=1)
        ]


class PlanExecutor:
    """Execute plans with retry and action limits, returning every outcome."""

    def __init__(self, invoke: Callable[..., Any], max_retries: int = 2):
        self.invoke = invoke
        self.max_retries = max_retries

    def execute(self, plan: TaskPlan) -> list[dict[str, Any]]:
        if plan.max_actions < 1:
            raise ValueError("max_actions must be positive")
        if len(plan.steps) > plan.max_actions:
            raise ValueError("Plan exceeds its maximum action budget.")
        results: list[dict[str, Any]] = []
        for index, step in enumerate(plan.steps, start=1):
            attempts = min(max(step.retries, 0), self.max_retries) + 1
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    value = self.invoke(step.tool, **step.arguments)
                    results.append(
                        {
                            "step": index,
                            "tool": step.tool,
                            "status": "ok",
                            "attempt": attempt,
                            "result": value,
                        }
                    )
                    break
                except Exception as error:
                    last_error = error
                    if attempt == attempts:
                        results.append(
                            {
                                "step": index,
                                "tool": step.tool,
                                "status": "error",
                                "attempt": attempt,
                                "error": str(error),
                            }
                        )
            if last_error is not None and results[-1]["status"] == "error":
                break
        return results
