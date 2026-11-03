from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .brain.ollama import OllamaError, OllamaClient


SECRET_PARTS = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
}
SECRET_PATTERNS = ("*secret*", "*token*", "*password*", "*apikey*", "*private*key*")
SUPPORTED_TEXT = {".txt", ".md", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".html", ".css", ".yaml", ".yml", ".toml", ".sh"}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    content: str
    source: str
    line_start: int
    line_end: int
    digest: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_secret_path(path: Path) -> bool:
    lowered = path.name.lower()
    if lowered in SECRET_PARTS or any(part.lower() in {".ssh", ".aws"} for part in path.parts):
        return True
    return any(path.match(pattern) or path.name.lower().endswith(pattern.strip("*")) for pattern in SECRET_PATTERNS)


def read_document(path: Path) -> str | None:
    if is_secret_path(path) or path.suffix.lower() not in SUPPORTED_TEXT | {".pdf", ".docx"}:
        return None
    try:
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        if path.suffix.lower() == ".docx":
            from docx import Document
            return "\n".join(paragraph.text for paragraph in Document(path).paragraphs)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".html":
            text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        if path.suffix.lower() == ".json":
            try:
                text = json.dumps(json.loads(text), indent=2)
            except json.JSONDecodeError:
                pass
        return text
    except (OSError, ImportError, ValueError):
        return None


def chunk_text(text: str, source: str, size: int = 900, overlap: int = 120) -> list[Chunk]:
    if size <= overlap or size < 1:
        raise ValueError("Chunk size must be greater than overlap.")
    lines = text.splitlines()
    chunks: list[Chunk] = []
    start = 0
    while start < len(lines):
        end = min(len(lines), start + size)
        content = "\n".join(lines[start:end]).strip()
        if content:
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunks.append(Chunk(f"{digest[:16]}-{start}", content, source, start + 1, end, digest))
        if end == len(lines):
            break
        start = max(start + 1, end - overlap)
    return chunks


class KnowledgeStore:
    """Local cited knowledge store with optional ChromaDB and lexical fallback."""

    def __init__(self, directory: Path, embedder: OllamaClient | None = None):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db_path = directory / "knowledge.sqlite3"
        self.manifest_path = directory / ".prakverse_manifest.json"
        self.embedder = embedder
        self._chroma = None
        try:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=str(directory / "chroma"))
            self._collection = self._chroma.get_or_create_collection("documents")
        except (ImportError, RuntimeError, ValueError):
            self._collection = None
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, content TEXT NOT NULL, source TEXT NOT NULL,
                    line_start INTEGER NOT NULL, line_end INTEGER NOT NULL,
                    digest TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    content, source, content='chunks', content_rowid='rowid'
                );
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
                    source TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )

    def ingest(self, root: Path) -> dict[str, int]:
        root = root.expanduser().resolve()
        paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        manifest: dict[str, str] = {}
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        counts = {"files": 0, "chunks": 0, "skipped": 0}
        for path in paths:
            if is_secret_path(path):
                counts["skipped"] += 1
                continue
            try:
                signature = f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
            except OSError:
                counts["skipped"] += 1
                continue
            previous_signature = manifest.get(str(path))
            manifest[str(path)] = signature
            if previous_signature == signature and self._source_exists(str(path)):
                continue
            text = read_document(path)
            if not text:
                counts["skipped"] += 1
                continue
            chunks = chunk_text(text, str(path))
            self._replace_source(str(path), chunks)
            counts["files"] += 1
            counts["chunks"] += len(chunks)
        self.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return counts

    def _source_exists(self, source: str) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM chunks WHERE source=? LIMIT 1", (source,)).fetchone() is not None

    def _replace_source(self, source: str, chunks: list[Chunk]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks WHERE source=?", (source,))
            connection.executemany(
                "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(c.chunk_id, c.content, c.source, c.line_start, c.line_end, c.digest, _now()) for c in chunks],
            )
        if self._collection is not None and chunks:
            self._collection.delete(where={"source": source})
            embeddings = self._embed([chunk.content for chunk in chunks])
            if embeddings:
                self._collection.add(
                    ids=[chunk.chunk_id for chunk in chunks],
                    documents=[chunk.content for chunk in chunks],
                    metadatas=[{"source": chunk.source, "line_start": chunk.line_start, "line_end": chunk.line_end} for chunk in chunks],
                    embeddings=embeddings,
                )

    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        if self.embedder is None:
            return None
        try:
            return [self.embedder.embed(text) for text in texts]
        except OllamaError:
            return None

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not query.strip() or limit < 1:
            return []
        if self._collection is not None and self.embedder is not None:
            try:
                embedding = self.embedder.embed(query)
                result = self._collection.query(query_embeddings=[embedding], n_results=limit)
                documents = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                if not documents:
                    raise OllamaError("ChromaDB returned no matches.")
                return [
                    {"content": content, "source": meta["source"], "line_start": meta["line_start"], "line_end": meta["line_end"]}
                    for content, meta in zip(documents, metadatas)
                ]
            except (OllamaError, KeyError, TypeError):
                pass
        terms = [term.lower() for term in re.findall(r"\w+", query) if len(term) > 2]
        with self._connect() as connection:
            rows = connection.execute("SELECT content, source, line_start, line_end FROM chunks ORDER BY created_at DESC").fetchall()
        ranked = sorted(rows, key=lambda row: sum(term in row["content"].lower() for term in terms), reverse=True)
        return [
            {"content": row["content"], "source": row["source"], "line_start": row["line_start"], "line_end": row["line_end"]}
            for row in ranked[:limit]
            if any(term in row["content"].lower() for term in terms)
        ]

    def add_fact(self, content: str, source: str = "confirmed") -> int:
        if not content.strip():
            raise ValueError("Fact cannot be empty.")
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO facts(content, source, created_at) VALUES (?, ?, ?)", (content.strip(), source, _now()))
            return int(cursor.lastrowid)

    def list_facts(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT id, content, source, created_at FROM facts ORDER BY id")]

    def forget_fact(self, fact_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM facts WHERE id=?", (fact_id,))
            return cursor.rowcount > 0

    def export(self, target: Path) -> None:
        payload = {"facts": self.list_facts(), "chunks": self._all_chunks()}
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _all_chunks(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT content, source, line_start, line_end FROM chunks ORDER BY source, line_start"
            ).fetchall()
        return [dict(row) for row in rows]

    def wipe(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM facts")
        self.manifest_path.unlink(missing_ok=True)
