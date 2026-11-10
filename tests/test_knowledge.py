from pathlib import Path

from prakverse.knowledge import KnowledgeStore, chunk_text, is_ignored_path, is_secret_path


def test_secret_paths_are_excluded() -> None:
    assert is_secret_path(Path("/tmp/project/.env"))
    assert is_secret_path(Path.home() / ".ssh" / "id_rsa")
    assert not is_secret_path(Path("/tmp/project/README.md"))
    assert is_ignored_path(Path("/tmp/project/node_modules/package/index.js"))


def test_ingest_and_citation_search(tmp_path: Path) -> None:
    sample = tmp_path / "sample"
    sample.mkdir()
    (sample / "notes.md").write_text(
        "PrakVerse indexes project notes locally.\nPriyumvada uses citations.",
        encoding="utf-8",
    )
    (sample / ".env").write_text("API_KEY=secret", encoding="utf-8")
    store = KnowledgeStore(tmp_path / "knowledge")

    result = store.ingest(sample)
    matches = store.search("citations")

    assert result["files"] == 1
    assert matches[0]["source"].endswith("notes.md")
    assert matches[0]["line_start"] == 1
    assert matches[0]["line_end"] == 2


def test_facts_require_nonempty_content_and_can_be_removed(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    fact_id = store.add_fact("Prefers local-first software.")
    assert store.list_facts()[0]["id"] == fact_id
    assert store.forget_fact(fact_id)
    assert store.list_facts() == []


def test_clear_root_removes_only_that_project(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "one.md").write_text("first project", encoding="utf-8")
    (second / "two.md").write_text("second project", encoding="utf-8")
    store = KnowledgeStore(tmp_path / "knowledge")
    store.ingest(first)
    store.ingest(second)
    store.clear_root(first)
    assert store.search("first") == []
    assert store.search("second")
