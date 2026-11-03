from pathlib import Path

import pytest

from prakverse.safety import ActionRisk, SafetyPolicy, requires_confirmation
from prakverse.tools.audit import AuditLog
from prakverse.tools.local import register_local_tools
from prakverse.tools.registry import ToolContext, ToolRegistry


def test_full_auto_does_not_require_confirmation() -> None:
    policy = SafetyPolicy()

    assert policy.execution_mode == "full_auto"
    assert not any(policy.requires_confirmation(risk) for risk in ActionRisk)
    assert not requires_confirmation(ActionRisk.DESTRUCTIVE)


def test_deny_list_blocks_dangerous_commands_and_paths() -> None:
    policy = SafetyPolicy()
    with pytest.raises(PermissionError):
        policy.check("sudo rm -rf /")
    with pytest.raises(PermissionError):
        policy.check("rm --no-preserve-root -rf /")
    with pytest.raises(PermissionError):
        policy.check("read", (str(Path.home() / ".ssh" / "id_rsa"),))
    with pytest.raises(PermissionError):
        policy.check("write", ("/tmp/.env",))


def test_registry_audits_success_and_dry_run(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    registry = ToolRegistry(ToolContext(SafetyPolicy(), audit))
    register_local_tools(registry)

    result = registry.invoke("system_info")

    assert "platform" in result
    records = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert '"status": "ok"' in records[0]

    dry_registry = ToolRegistry(ToolContext(SafetyPolicy(), audit, dry_run=True))
    register_local_tools(dry_registry)
    result = dry_registry.invoke("write_file", path=str(tmp_path / "x"), content="nope")
    assert result["dry_run"] is True
    assert not (tmp_path / "x").exists()
