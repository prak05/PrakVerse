from __future__ import annotations

import os
import socket
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("PRAKVERSE_DATA_DIR", PROJECT_ROOT / "data")).expanduser()
MEMORY_DB = Path(
    os.environ.get("PRAKVERSE_MEMORY_DB", DATA_DIR / "memory.sqlite3")
).expanduser()
AUDIT_LOG = Path(
    os.environ.get("PRAKVERSE_AUDIT_LOG", DATA_DIR / "audit.jsonl")
).expanduser()
MEMORY_DIR = Path(
    os.environ.get("PRAKVERSE_MEMORY_DIR", DATA_DIR / "knowledge")
).expanduser()

ASSISTANT_NAME = os.environ.get("PRAKVERSE_ASSISTANT_NAME", "Priyumvada")
PLATFORM_NAME = "PrakVerse"

CHAT_MODEL = os.environ.get("PRAKVERSE_CHAT_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.environ.get("PRAKVERSE_EMBED_MODEL", "nomic-embed-text")

def _default_ollama_url() -> str:
    for port in (11435, 11434):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return f"http://127.0.0.1:{port}"
        except OSError:
            continue
    return "http://127.0.0.1:11434"


OLLAMA_URL = os.environ.get("PRAKVERSE_OLLAMA_URL", _default_ollama_url())
VOICE_MODEL = os.environ.get("PRAKVERSE_WHISPER_MODEL", "base")
PIPER_MODEL = os.environ.get("PRAKVERSE_PIPER_MODEL", "")
SKILLS_DIR = Path(os.environ.get("PRAKVERSE_SKILLS_DIR", PROJECT_ROOT / "skills")).expanduser()
SCHEDULE_DB = Path(os.environ.get("PRAKVERSE_SCHEDULE_DB", DATA_DIR / "schedules.sqlite3")).expanduser()
MCP_CONFIG = Path(os.environ.get("PRAKVERSE_MCP_CONFIG", PROJECT_ROOT / "mcp.json")).expanduser()
INTEL_CATALOG = Path(
    os.environ.get("PRAKVERSE_INTEL_CATALOG", PROJECT_ROOT / "intel_projects.json")
).expanduser()
