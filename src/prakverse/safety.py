from __future__ import annotations

from enum import Enum


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


def requires_confirmation(risk: ActionRisk) -> bool:
    return risk in CONFIRMATION_REQUIRED

