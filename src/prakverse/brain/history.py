from __future__ import annotations

from collections import deque

from .ollama import ChatMessage


class ConversationHistory:
    """Conversation state with a bounded number of user/assistant turns."""

    def __init__(self, system_prompt: str, max_turns: int = 12):
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self._turns: deque[tuple[ChatMessage, ChatMessage]] = deque(
            maxlen=max_turns
        )

    def add_turn(self, user_content: str, assistant_content: str) -> None:
        self._turns.append(
            (
                ChatMessage("user", user_content),
                ChatMessage("assistant", assistant_content),
            )
        )

    def messages(self, user_content: str) -> list[ChatMessage]:
        messages = [ChatMessage("system", self.system_prompt)]
        for user, assistant in self._turns:
            messages.extend((user, assistant))
        messages.append(ChatMessage("user", user_content))
        return messages

    @property
    def turn_count(self) -> int:
        return len(self._turns)
