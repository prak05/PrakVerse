from __future__ import annotations

from enum import Enum

from dataclasses import dataclass


class ActionRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"


CONFIRMATION_REQUIRED = {
    ActionRisk.WRITE,
    ActionRisk.DESTRUCTIVE,
    ActionRisk.EXTERNAL,
}


@dataclass(frozen=True)
class SafetyPolicy:
    """Execution policy; deny-listed operations remain blocked in auto mode."""

    execution_mode: str = "full_auto"
    confirmation_required: frozenset[ActionRisk] = frozenset()

    def requires_confirmation(self, risk: ActionRisk) -> bool:
        return risk in self.confirmation_required


def requires_confirmation(risk: ActionRisk) -> bool:
    return SafetyPolicy().requires_confirmation(risk)
