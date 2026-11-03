from pathlib import Path
from types import SimpleNamespace

from prakverse.tools.browser import BrowserController, register_browser_tools
from prakverse.tools.gui import display_backend, register_gui_tools
from prakverse.tools.registry import ToolContext, ToolRegistry
from prakverse.safety import SafetyPolicy
from prakverse.tools.audit import AuditLog


class FakeLocator:
    def __init__(self):
        self.filled = None
        self.clicked = False

    def inner_text(self):
        return "sample page"

    def click(self):
        self.clicked = True

    def fill(self, value):
        self.filled = value


class FakePage:
    url = "https://example.test"

    def __init__(self):
        self.locator_instance = FakeLocator()
        self.screenshot_path = None

    def title(self):
        return "Example"

    def goto(self, url, wait_until):
        self.url = url

    def locator(self, _selector):
        return self.locator_instance

    def screenshot(self, path, full_page):
        self.screenshot_path = (path, full_page)


def test_browser_controller_actions_use_current_page(tmp_path: Path) -> None:
    controller = BrowserController(page=FakePage())
    assert controller.extract() == "sample page"
    assert controller.fill("#name", "Priyu") == "filled #name"
    assert controller.click("#submit")["title"] == "Example"
    assert controller.screenshot(str(tmp_path / "page.png")).endswith("page.png")


def test_browser_tools_are_registered_and_gui_status_is_read_only(tmp_path: Path) -> None:
    registry = ToolRegistry(
        ToolContext(SafetyPolicy(), AuditLog(tmp_path / "audit.jsonl"))
    )
    register_browser_tools(registry, BrowserController(page=FakePage()))
    register_gui_tools(registry)

    assert "browser_search" in registry.names()
    assert "gui_status" in registry.names()
    assert registry.invoke("gui_status")["display"] in {"wayland", "x11", "none"}


def test_display_backend_is_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    assert display_backend() == "none"
