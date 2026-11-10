from __future__ import annotations

import json
import errno
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .brain.history import ConversationHistory
from .brain.ollama import OllamaClient, OllamaError
from .brain.persona import load_system_prompt
from .brain.session import ChatSession
from .config import ASSISTANT_NAME, CHAT_MODEL, EMBED_MODEL, INTEL_CATALOG, MEMORY_DIR, OLLAMA_URL
from .intel import CentralIntel
from .knowledge import KnowledgeStore


WEB_DIR = Path(__file__).with_name("web_assets")
_session_lock = threading.Lock()
_session: ChatSession | None = None


def _knowledge() -> KnowledgeStore:
    return KnowledgeStore(
        MEMORY_DIR,
        embedder=OllamaClient(OLLAMA_URL, EMBED_MODEL),
    )


def _intel() -> CentralIntel:
    return CentralIntel(_knowledge(), INTEL_CATALOG)


def _chat_session() -> ChatSession:
    global _session
    with _session_lock:
        if _session is None:
            _session = ChatSession(
                OllamaClient(OLLAMA_URL, CHAT_MODEL),
                ConversationHistory(load_system_prompt(), 12),
            )
        return _session


class PrakVerseHandler(BaseHTTPRequestHandler):
    server_version = "PrakVerse/0.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: object) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _request_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(length)
        payload = json.loads(raw or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("JSON request must be an object.")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            try:
                projects = _intel().status()
            except ValueError:
                projects = []
            self._json(
                HTTPStatus.OK,
                {
                    "assistant": ASSISTANT_NAME,
                    "model": CHAT_MODEL,
                    "ollama_url": OLLAMA_URL,
                    "projects": projects,
                },
            )
            return
        if parsed.path == "/api/health":
            try:
                OllamaClient(OLLAMA_URL, CHAT_MODEL).chat(
                    ConversationHistory("health check", 1).messages("Reply with OK.")
                )
                self._json(HTTPStatus.OK, {"ollama": "ready", "model": CHAT_MODEL})
            except OllamaError as error:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ollama": "offline", "error": str(error)})
            return
        if parsed.path == "/api/intel":
            self._json(HTTPStatus.OK, {"projects": _intel().status()})
            return
        if parsed.path.startswith("/api/recall"):
            query = parse_qs(parsed.query).get("q", [""])[0]
            results = _knowledge().search(query)
            self._json(HTTPStatus.OK, {"results": results})
            return
        self._serve_asset(parsed.path)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            payload = self._request_json()
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("message is required")
            context = _knowledge().search(message, limit=3)
            if context:
                cited = "\n\n".join(
                    f"[{item['source']}:{item['line_start']}-{item['line_end']}]\n{item['content']}"
                    for item in context
                )
                prompt = (
                    "Use the following local Central Intel context when relevant. "
                    "Do not invent facts and mention the source path when relying on it.\n\n"
                    f"{cited}\n\nUser request: {message}"
                )
            else:
                prompt = message
            response = _chat_session().respond(prompt)
            self._json(
                HTTPStatus.OK,
                {
                    "response": response,
                    "sources": [
                        {
                            "source": item["source"],
                            "line_start": item["line_start"],
                            "line_end": item["line_end"],
                        }
                        for item in context
                    ],
                },
            )
        except (ValueError, OllamaError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _serve_asset(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.removeprefix("/")
        if relative not in {"index.html", "manifest.webmanifest", "sw.js", "icon.svg"}:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        target = WEB_DIR / relative
        if not target.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "Asset not found"})
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, target.read_bytes(), content_type)


class PrakVerseServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    url = f"http://{host}:{port}"
    try:
        server = PrakVerseServer((host, port), PrakVerseHandler)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        print(f"PrakVerse is already running at {url}")
        if open_browser:
            webbrowser.open(url)
        return
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    print(f"PrakVerse app: {url}")
    print("Chrome: use the install icon in the address bar, then pin the app to the dock.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
