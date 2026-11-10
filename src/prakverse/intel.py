from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeStore


@dataclass(frozen=True)
class IntelProject:
    name: str
    path: Path
    domain: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CentralIntel:
    """Named project catalog backed by the shared PrakVerse knowledge store."""

    def __init__(self, knowledge: KnowledgeStore, catalog_path: Path):
        self.knowledge = knowledge
        self.catalog_path = catalog_path
        self.db_path = knowledge.directory / "central_intel.sqlite3"
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    name TEXT PRIMARY KEY, path TEXT NOT NULL, domain TEXT NOT NULL,
                    last_sync TEXT, files INTEGER NOT NULL DEFAULT 0,
                    chunks INTEGER NOT NULL DEFAULT 0, skipped INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending'
                )"""
            )

    def projects(self) -> list[IntelProject]:
        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid Central Intel catalog: {self.catalog_path}") from error
        projects = []
        for item in data.get("projects", []):
            name, path, domain = item.get("name"), item.get("path"), item.get("domain", "")
            if not isinstance(name, str) or not isinstance(path, str):
                raise ValueError("Every Central Intel project needs a name and path.")
            projects.append(IntelProject(name, Path(path).expanduser(), str(domain)))
        return projects

    def sync(self, names: set[str] | None = None) -> list[dict[str, Any]]:
        outcomes = []
        for project in self.projects():
            if names and project.name not in names:
                continue
            if not project.path.exists():
                outcome = {"name": project.name, "status": "missing", "path": str(project.path)}
            else:
                self.knowledge.clear_root(project.path)
                counts = self.knowledge.ingest(project.path)
                outcome = {"name": project.name, "status": "ok", "path": str(project.path), **counts}
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    """INSERT INTO projects(name, path, domain, last_sync, files, chunks, skipped, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(name) DO UPDATE SET path=excluded.path, domain=excluded.domain,
                       last_sync=excluded.last_sync, files=excluded.files, chunks=excluded.chunks,
                       skipped=excluded.skipped, status=excluded.status""",
                    (
                        project.name,
                        str(project.path),
                        project.domain,
                        _now(),
                        outcome.get("files", 0),
                        outcome.get("chunks", 0),
                        outcome.get("skipped", 0),
                        outcome["status"],
                    ),
                )
            outcomes.append(outcome)
        return outcomes

    def status(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT name, path, domain, last_sync, files, chunks, skipped, status "
                "FROM projects ORDER BY name"
            ).fetchall()
        return [
            dict(
                zip(
                    ("name", "path", "domain", "last_sync", "files", "chunks", "skipped", "status"),
                    row,
                )
            )
            for row in rows
        ]
