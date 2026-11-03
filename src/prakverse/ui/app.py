from __future__ import annotations

from pathlib import Path

from ..config import ASSISTANT_NAME, CHAT_MODEL, MEMORY_DB, MEMORY_DIR

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Label, Log, Static
except ImportError as error:  # pragma: no cover - depends on optional extra
    raise RuntimeError("Textual is not installed.") from error


class PrakVerseApp(App[None]):
    """Local dashboard with chat input, status, and live log panes."""

    TITLE = "PrakVerse — Powered by Priyumvada"
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #status { width: 32; border: solid green; padding: 1; }
    #activity { width: 1fr; border: solid cyan; }
    #prompt { dock: bottom; margin: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield Vertical(
                Static("PRIYUMVADA", id="assistant"),
                Label(f"Model: {CHAT_MODEL}"),
                Label(f"Memory DB: {MEMORY_DB}"),
                Label(f"Knowledge: {MEMORY_DIR}"),
                Label("Mode: local / full-auto / deny-list protected"),
                id="status",
            )
            yield Log(id="activity", highlight=True)
        yield Input(placeholder="Ask Priyu...", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#activity", Log).write_line(
            "PrakVerse dashboard ready. Type a request or press Ctrl+C to exit."
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        self.query_one("#activity", Log).write_line(f"You> {prompt}")
        self.query_one("#activity", Log).write_line(
            "Chat backend is available through `prak chat`; tool orchestration remains explicit."
        )
        event.input.value = ""
