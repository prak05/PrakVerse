import json
from pathlib import Path

import pytest

from prakverse.control.mcp import MCPClient


def test_empty_mcp_config_loads(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"servers": {}}), encoding="utf-8")
    assert MCPClient().connect_config(config) == {}


def test_invalid_mcp_config_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid MCP"):
        MCPClient().connect_config(config)
