from __future__ import annotations

from .history import ConversationHistory
from .ollama import OllamaClient


class ChatSession:
    """Coordinates bounded conversation history and local model responses."""

    def __init__(self, client: OllamaClient, history: ConversationHistory):
        self.client = client
        self.history = history

    def respond(self, user_content: str) -> str:
        prompt = user_content.strip()
        if not prompt:
            raise ValueError("Message cannot be empty.")
        response = self.client.chat(self.history.messages(prompt))
        self.history.add_turn(prompt, response)
        return response
