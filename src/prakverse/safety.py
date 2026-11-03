from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from pathlib import Path


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

    def check(self, operation: str, paths: tuple[str, ...] = ()) -> None:
        """Raise PermissionError when a deny-listed operation is detected."""
        normalized = operation.lower()
        if re.search(r"\bsudo\b|\bmkfs(?:\.[\w-]+)?\b|\bfdisk\b|\bparted\b", normalized):
            raise PermissionError("Blocked by safety policy: privileged or disk operation.")
        if re.search(r"rm\s+(?:-[a-z]*r[a-z]*\s+)?(?:/|~)(?:\s|$)", normalized):
            raise PermissionError("Blocked by safety policy: destructive root-path deletion.")
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            parts = {part.lower() for part in path.parts}
            if ".ssh" in parts or path.name.lower() in {
                ".env",
                "credentials",
                "credentials.json",
                "token",
                "token.txt",
                "id_rsa",
            }:
                raise PermissionError("Blocked by safety policy: credential or SSH path.")


def requires_confirmation(risk: ActionRisk) -> bool:
    return SafetyPolicy().requires_confirmation(risk)
