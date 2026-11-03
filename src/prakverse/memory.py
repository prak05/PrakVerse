from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Memory:
    memory_id: int
    content: str
    source: str
    created_at: str


class MemoryStore:
    """Small, portable local memory store using SQLite FTS5."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    source,
                    content='memories',
                    content_rowid='id'
                );
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, source)
                    VALUES (new.id, new.content, new.source);
                END;
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, source)
                    VALUES ('delete', old.id, old.content, old.source);
                END;
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, source)
                    VALUES ('delete', old.id, old.content, old.source);
                    INSERT INTO memories_fts(rowid, content, source)
                    VALUES (new.id, new.content, new.source);
                END;
                """
            )

    def add(self, content: str, source: str = "manual") -> Memory:
        normalized = " ".join(content.split())
        if not normalized:
            raise ValueError("Memory content cannot be empty.")
        source = " ".join(source.split()) or "manual"
        created_at = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO memories(content, source, created_at) VALUES (?, ?, ?)",
                (normalized, source, created_at),
            )
            memory_id = int(cursor.lastrowid)
        return Memory(memory_id, normalized, source, created_at)

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        normalized = " ".join(query.split())
        if not normalized:
            return []
        if limit < 1:
            raise ValueError("Search limit must be positive.")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT m.id, m.content, m.source, m.created_at
                FROM memories_fts f
                JOIN memories m ON m.id = f.rowid
                WHERE memories_fts MATCH ?
                ORDER BY bm25(memories_fts), m.created_at DESC
                LIMIT ?
                """,
                (normalized, min(limit, 100)),
            ).fetchall()
        return [Memory(row["id"], row["content"], row["source"], row["created_at"]) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM memories").fetchone()
        return int(row["count"])

