"""Local reasoning components for PrakVerse."""

from .ollama import OllamaClient, OllamaError
from .persona import load_system_prompt

__all__ = ["OllamaClient", "OllamaError", "load_system_prompt"]
