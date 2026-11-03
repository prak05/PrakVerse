from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ScheduledTask:
    task_id: int
    name: str
    interval_seconds: int
    payload: str
    next_run: str
    enabled: bool


class Scheduler:
    """Small persistent interval scheduler; it does not spawn hidden threads."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
                    interval_seconds INTEGER NOT NULL, payload TEXT NOT NULL,
                    next_run TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
                )"""
            )

    def add(self, name: str, interval_seconds: int, payload: str) -> ScheduledTask:
        if not name.strip() or interval_seconds < 1:
            raise ValueError("A task name and positive interval are required.")
        next_run = _now() + timedelta(seconds=interval_seconds)
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                """INSERT INTO scheduled_tasks
                   (name, interval_seconds, payload, next_run) VALUES (?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET interval_seconds=excluded.interval_seconds,
                   payload=excluded.payload, next_run=excluded.next_run, enabled=1""",
                (name.strip(), interval_seconds, payload, next_run.isoformat()),
            )
            task_id = int(cursor.lastrowid or connection.execute(
                "SELECT id FROM scheduled_tasks WHERE name=?", (name.strip(),)
            ).fetchone()[0])
        return ScheduledTask(task_id, name.strip(), interval_seconds, payload, next_run.isoformat(), True)

    def list(self) -> list[ScheduledTask]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT id, name, interval_seconds, payload, next_run, enabled FROM scheduled_tasks ORDER BY id"
            ).fetchall()
        return [ScheduledTask(row[0], row[1], row[2], row[3], row[4], bool(row[5])) for row in rows]

    def run_due(self, execute: Callable[[str], Any]) -> list[dict[str, Any]]:
        now = _now()
        outcomes = []
        for task in self.list():
            if not task.enabled or datetime.fromisoformat(task.next_run) > now:
                continue
            try:
                result = execute(task.payload)
                status = "ok"
                error = ""
            except Exception as exc:
                result = None
                status = "error"
                error = str(exc)
            next_run = now + timedelta(seconds=task.interval_seconds)
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    "UPDATE scheduled_tasks SET next_run=? WHERE id=?",
                    (next_run.isoformat(), task.task_id),
                )
            outcomes.append({"name": task.name, "status": status, "result": result, "error": error})
        return outcomes
