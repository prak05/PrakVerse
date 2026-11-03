from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MCPServer:
    name: str
    process: subprocess.Popen[str]
    request_id: int = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        if self.process.stdout is None:
            raise RuntimeError("MCP server has no stdout.")
        for line in self.process.stdout:
            response = json.loads(line)
            if response.get("id") == self.request_id:
                if "error" in response:
                    raise RuntimeError(str(response["error"]))
                return response
        raise RuntimeError("MCP server closed before replying.")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()


class MCPClient:
    """Minimal local stdio MCP client for configured servers."""

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}

    def connect(self, name: str, command: list[str], cwd: str | None = None) -> MCPServer:
        if not command:
            raise ValueError("MCP command cannot be empty.")
        process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1
        )
        server = MCPServer(name, process)
        self.servers[name] = server
        return server

    def connect_config(self, path: Path) -> dict[str, MCPServer]:
        """Start every configured stdio server from a local JSON config."""
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid MCP configuration: {path}") from error
        for name, settings in config.get("servers", {}).items():
            command = settings.get("command")
            args = settings.get("args", [])
            if not isinstance(command, str) or not isinstance(args, list):
                raise ValueError(f"Invalid MCP command configuration for {name}.")
            self.connect(name, [command, *[str(arg) for arg in args]], settings.get("cwd"))
        return dict(self.servers)

    def close(self) -> None:
        for server in self.servers.values():
            server.close()
        self.servers.clear()
