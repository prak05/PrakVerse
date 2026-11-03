from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("PRAKVERSE_DATA_DIR", PROJECT_ROOT / "data")).expanduser()
MEMORY_DB = Path(
    os.environ.get("PRAKVERSE_MEMORY_DB", DATA_DIR / "memory.sqlite3")
).expanduser()
AUDIT_LOG = Path(
    os.environ.get("PRAKVERSE_AUDIT_LOG", DATA_DIR / "audit.jsonl")
).expanduser()

ASSISTANT_NAME = os.environ.get("PRAKVERSE_ASSISTANT_NAME", "Priyumvada")
PLATFORM_NAME = "PrakVerse"

CHAT_MODEL = os.environ.get("PRAKVERSE_CHAT_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.environ.get("PRAKVERSE_EMBED_MODEL", "nomic-embed-text")
OLLAMA_URL = os.environ.get("PRAKVERSE_OLLAMA_URL", "http://127.0.0.1:11434")
