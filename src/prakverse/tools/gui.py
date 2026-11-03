from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..safety import ActionRisk, SafetyPolicy
from .registry import ToolRegistry


def display_backend() -> str:
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "none"


def _pyautogui():
    try:
        import pyautogui
    except ImportError as error:
        raise RuntimeError(
            "GUI control requires pyautogui. Run: pip install -e '.[gui]'"
        ) from error
    return pyautogui


def register_gui_tools(
    registry: ToolRegistry, policy: SafetyPolicy | None = None
) -> None:
    active_policy = policy or registry.context.policy

    def gui_status() -> dict[str, str]:
        return {"display": display_backend()}

    def gui_screenshot(path: str) -> str:
        active_policy.check("gui_screenshot", (path,))
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        _pyautogui().screenshot(str(target))
        return str(target)

    def gui_move(x: int, y: int) -> str:
        active_policy.check("gui_move")
        _pyautogui().moveTo(x, y)
        return f"moved pointer to {x},{y}"

    def gui_click(x: int, y: int) -> str:
        active_policy.check("gui_click")
        _pyautogui().click(x, y)
        return f"clicked at {x},{y}"

    def gui_type(text: str) -> str:
        active_policy.check("gui_type")
        _pyautogui().write(text)
        return "typed text"

    def gui_key(key: str) -> str:
        active_policy.check("gui_key")
        _pyautogui().press(key)
        return f"pressed {key}"

    def window_list() -> list[str]:
        if shutil.which("wmctrl"):
            result = subprocess.run(
                ["wmctrl", "-l"], check=True, capture_output=True, text=True
            )
            return result.stdout.splitlines()
        if shutil.which("xdotool"):
            result = subprocess.run(
                ["xdotool", "search", "--name", ".*", "getwindowname", "%@"],
                check=False,
                capture_output=True,
                text=True,
            )
            return [line for line in result.stdout.splitlines() if line]
        raise RuntimeError("Install wmctrl or xdotool for window listing.")

    registry.register("gui_status", ActionRisk.READ, gui_status)
    registry.register("gui_screenshot", ActionRisk.WRITE, gui_screenshot)
    registry.register("gui_move", ActionRisk.WRITE, gui_move)
    registry.register("gui_click", ActionRisk.WRITE, gui_click)
    registry.register("gui_type", ActionRisk.WRITE, gui_type)
    registry.register("gui_key", ActionRisk.WRITE, gui_key)
    registry.register("window_list", ActionRisk.READ, window_list)
