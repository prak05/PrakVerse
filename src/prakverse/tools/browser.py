from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from ..safety import ActionRisk, SafetyPolicy
from .registry import ToolRegistry


@dataclass
class BrowserController:
    """A small Playwright controller with one reusable local browser session."""

    headless: bool = True
    _playwright: Any = None
    _browser: Any = None
    page: Any = None

    def _ensure_page(self) -> Any:
        if self.page is None:
            raise RuntimeError("Browser is not open. Use browser_open first.")
        return self.page

    def open(self, url: str) -> dict[str, str]:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Browser URLs must use http:// or https://.")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install -e '.[browser]' "
                "and then: playwright install chromium"
            ) from error
        if self.page is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self.page = self._browser.new_page()
        self.page.goto(url, wait_until="domcontentloaded")
        return {"url": self.page.url, "title": self.page.title()}

    def search(self, query: str, engine: str = "duckduckgo") -> dict[str, str]:
        if engine != "duckduckgo":
            raise ValueError("Only the privacy-friendly DuckDuckGo engine is supported.")
        return self.open(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")

    def extract(self, selector: str = "body") -> str:
        page = self._ensure_page()
        return str(page.locator(selector).inner_text())

    def click(self, selector: str) -> dict[str, str]:
        page = self._ensure_page()
        page.locator(selector).click()
        return {"url": page.url, "title": page.title()}

    def fill(self, selector: str, value: str) -> str:
        self._ensure_page().locator(selector).fill(value)
        return f"filled {selector}"

    def screenshot(self, path: str) -> str:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_page().screenshot(path=str(target), full_page=True)
        return str(target)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = self._browser = self.page = None


def register_browser_tools(
    registry: ToolRegistry,
    controller: BrowserController | None = None,
    policy: SafetyPolicy | None = None,
) -> BrowserController:
    controller = controller or BrowserController()
    active_policy = policy or registry.context.policy

    def browser_open(url: str) -> dict[str, str]:
        active_policy.check("browser_open")
        return controller.open(url)

    def browser_search(query: str) -> dict[str, str]:
        active_policy.check("browser_search")
        return controller.search(query)

    def browser_extract(selector: str = "body") -> str:
        active_policy.check("browser_extract")
        return controller.extract(selector)

    def browser_click(selector: str) -> dict[str, str]:
        active_policy.check("browser_click")
        return controller.click(selector)

    def browser_fill(selector: str, value: str) -> str:
        active_policy.check("browser_fill")
        return controller.fill(selector, value)

    def browser_screenshot(path: str) -> str:
        active_policy.check("browser_screenshot", (path,))
        return controller.screenshot(path)

    registry.register("browser_open", ActionRisk.EXTERNAL, browser_open)
    registry.register("browser_search", ActionRisk.EXTERNAL, browser_search)
    registry.register("browser_extract", ActionRisk.READ, browser_extract)
    registry.register("browser_click", ActionRisk.EXTERNAL, browser_click)
    registry.register("browser_fill", ActionRisk.EXTERNAL, browser_fill)
    registry.register("browser_screenshot", ActionRisk.WRITE, browser_screenshot)
    return controller
