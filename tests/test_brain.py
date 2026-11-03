import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from prakverse.brain.history import ConversationHistory
from prakverse.brain.ollama import ChatMessage, OllamaClient, OllamaError
from prakverse.brain.persona import load_system_prompt
from prakverse.brain.session import ChatSession


class FakeResponse:
    def __init__(self, lines: list[bytes]):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def __iter__(self):
        return iter(self.lines)


def test_stream_chat_posts_messages_and_yields_chunks() -> None:
    response = FakeResponse(
        [
            json.dumps({"message": {"content": "Hello "}}).encode(),
            json.dumps({"message": {"content": "Priyu!"}}).encode(),
        ]
    )
    with patch("prakverse.brain.ollama.request.urlopen", return_value=response) as urlopen:
        chunks = list(
            OllamaClient("http://localhost:11434", "qwen2.5:3b").stream_chat(
                [ChatMessage("user", "Hi")]
            )
        )

    assert chunks == ["Hello ", "Priyu!"]
    body = json.loads(urlopen.call_args.args[0].data)
    assert body["model"] == "qwen2.5:3b"
    assert body["stream"] is True


def test_stream_chat_reports_server_errors() -> None:
    response = FakeResponse([json.dumps({"error": "model missing"}).encode()])
    with patch("prakverse.brain.ollama.request.urlopen", return_value=response):
        with pytest.raises(OllamaError, match="model missing"):
            list(OllamaClient("http://localhost:11434", "missing").stream_chat([]))


def test_history_rolls_old_turns_and_session_saves_response() -> None:
    history = ConversationHistory("system", max_turns=1)
    history.add_turn("old", "answer")
    history.add_turn("new", "answer 2")
    assert [message.content for message in history.messages("latest")] == [
        "system",
        "new",
        "answer 2",
        "latest",
    ]

    class FakeClient:
        def chat(self, messages):
            assert messages[-1].content == "hello"
            return "Hi there 🙂"

    session = ChatSession(FakeClient(), ConversationHistory("system"))
    assert session.respond("hello") == "Hi there 🙂"
    assert session.history.turn_count == 1


def test_persona_prompt_can_be_edited_in_config(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text('assistant:\n  system_prompt: "Custom Priyu"\n', encoding="utf-8")
    assert load_system_prompt(config) == "Custom Priyu"
