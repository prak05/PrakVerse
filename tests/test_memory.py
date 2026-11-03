from pathlib import Path

import pytest

from prakverse.memory import MemoryStore


def test_memory_round_trip(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")
    saved = store.add("PrakVerse should index LinkedIn Indo.", "project")

    results = store.search("LinkedIn Indo")

    assert saved.memory_id == 1
    assert results[0].content == "PrakVerse should index LinkedIn Indo."
    assert results[0].source == "project"


def test_empty_memory_is_rejected(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")

    with pytest.raises(ValueError, match="cannot be empty"):
        store.add("   ")


def test_search_limit_must_be_positive(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")

    with pytest.raises(ValueError, match="must be positive"):
        store.search("anything", 0)

