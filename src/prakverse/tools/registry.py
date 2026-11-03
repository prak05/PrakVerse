from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..config import AUDIT_LOG
from ..safety import ActionRisk, SafetyPolicy
from .audit import AuditLog


ToolFunction = Callable[..., Any]


@dataclass(frozen=True)
class ToolContext:
    policy: SafetyPolicy
    audit: AuditLog
    dry_run: bool = False


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    risk: ActionRisk
    function: ToolFunction


class ToolRegistry:
    def __init__(
        self,
        context: ToolContext | None = None,
    ):
        self.context = context or ToolContext(SafetyPolicy(), AuditLog(AUDIT_LOG))
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, name: str, risk: ActionRisk, function: ToolFunction) -> None:
        if not name or name in self._tools:
            raise ValueError(f"Invalid or duplicate tool name: {name!r}")
        self._tools[name] = RegisteredTool(name, risk, function)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def invoke(self, name: str, **arguments: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        tool = self._tools[name]
        try:
            command = arguments.get("command")
            paths = tuple(
                str(arguments[key])
                for key in ("path", "root")
                if key in arguments and isinstance(arguments[key], str)
            )
            self.context.policy.check(str(command or name), paths)
            if self.context.dry_run:
                self.context.audit.append(
                    tool=name,
                    arguments=arguments,
                    status="dry_run",
                    detail=f"Would execute {tool.risk.value} tool.",
                )
                return {"dry_run": True, "tool": name, "arguments": arguments}
            result = tool.function(**arguments)
            self.context.audit.append(
                tool=name, arguments=arguments, status="ok", detail="completed"
            )
            return result
        except Exception as error:
            self.context.audit.append(
                tool=name, arguments=arguments, status="blocked_or_error", detail=str(error)
            )
            raise
