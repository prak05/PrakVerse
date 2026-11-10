import json
import threading
import urllib.request
from pathlib import Path

from prakverse.web import PrakVerseServer, PrakVerseHandler


def test_pwa_assets_are_served(tmp_path: Path, monkeypatch) -> None:
    server = PrakVerseServer(("127.0.0.1", 0), PrakVerseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base + "/") as response:
            assert response.status == 200
            assert "PrakVerse" in response.read().decode()
        with urllib.request.urlopen(base + "/manifest.webmanifest") as response:
            manifest = json.loads(response.read())
            assert manifest["display"] == "standalone"
    finally:
        server.shutdown()
        server.server_close()
