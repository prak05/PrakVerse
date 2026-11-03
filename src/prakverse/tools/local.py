from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from ..safety import ActionRisk, SafetyPolicy
from .registry import ToolRegistry


def register_local_tools(registry: ToolRegistry, policy: SafetyPolicy | None = None) -> None:
    active_policy = policy or registry.context.policy

    def shell(command: str) -> str:
        active_policy.check(command)
        return subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, timeout=60
        ).stdout

    def read_file(path: str) -> str:
        active_policy.check("read_file", (path,))
        return Path(path).expanduser().read_text(encoding="utf-8")

    def write_file(path: str, content: str) -> str:
        active_policy.check("write_file", (path,))
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def search_files(root: str, pattern: str = "*") -> list[str]:
        active_policy.check("search_files", (root,))
        return [str(path) for path in Path(root).expanduser().rglob(pattern)]

    def system_info() -> dict[str, str]:
        return {
            "os": os.name,
            "platform": subprocess.run(
                ["uname", "-a"], check=False, capture_output=True, text=True
            ).stdout.strip(),
        }

    def web_fetch(url: str) -> str:
        active_policy.check("web_fetch")
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")

    def list_apps() -> list[str]:
        result = subprocess.run(
            ["ps", "-eo", "comm="], check=False, capture_output=True, text=True
        )
        return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})

    def open_app(command: str) -> str:
        active_policy.check("open_app")
        executable = command.split()[0]
        if shutil.which(executable) is None:
            raise FileNotFoundError(f"Application not found: {executable}")
        subprocess.Popen(command.split(), start_new_session=True)
        return f"started {command}"

    def clipboard_read() -> str:
        active_policy.check("clipboard_read")
        for executable in ("wl-paste", "xclip"):
            if shutil.which(executable):
                command = [executable] if executable == "wl-paste" else [executable, "-selection", "clipboard", "-o"]
                return subprocess.run(command, check=True, capture_output=True, text=True).stdout
        raise RuntimeError("No wl-paste or xclip executable is available.")

    def clipboard_write(content: str) -> str:
        active_policy.check("clipboard_write")
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=content, check=True, text=True)
        elif shutil.which("xclip"):
            subprocess.run(
                ["xclip", "-selection", "clipboard"], input=content, check=True, text=True
            )
        else:
            raise RuntimeError("No wl-copy or xclip executable is available.")
        return "clipboard updated"

    registry.register("shell", ActionRisk.WRITE, shell)
    registry.register("read_file", ActionRisk.READ, read_file)
    registry.register("write_file", ActionRisk.WRITE, write_file)
    registry.register("search_files", ActionRisk.READ, search_files)
    registry.register("system_info", ActionRisk.READ, system_info)
    registry.register("web_fetch", ActionRisk.EXTERNAL, web_fetch)
    registry.register("list_apps", ActionRisk.READ, list_apps)
    registry.register("open_app", ActionRisk.WRITE, open_app)
    registry.register("clipboard_read", ActionRisk.READ, clipboard_read)
    registry.register("clipboard_write", ActionRisk.WRITE, clipboard_write)
