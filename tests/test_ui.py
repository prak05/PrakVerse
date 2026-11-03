from pathlib import Path


def test_systemd_service_is_user_scoped() -> None:
    service = Path("systemd/prakverse.service").read_text(encoding="utf-8")
    assert "systemctl" not in service
    assert "ExecStart=%h/PrakVerse/.venv/bin/prak up" in service


def test_architecture_documents_local_default() -> None:
    text = Path("ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Local Ollama brain" in text
    assert "Safety-gated tool registry" in text
