from __future__ import annotations

import os
from pathlib import Path

from ..config import ASSISTANT_NAME, PROJECT_ROOT


DEFAULT_SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, also called Priyu.
You are PrakVerse's private local assistant.
Use she/her pronouns. Be concise, witty, practical, and warm; occasional light
emojis are welcome. Never claim to have performed an action you did not perform.
Ask for confirmation before risky actions. Do not invent personal facts about
Prakhar; say when information is unavailable."""


def _configured_prompt(config_path: Path) -> str | None:
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return None
    marker = "system_prompt:"
    for line in text.splitlines():
        if line.strip().startswith(marker):
            value = line.split(":", 1)[1].strip().strip('"\'')
            return value or None
    return None


def load_system_prompt(config_path: Path | None = None) -> str:
    """Load the editable prompt from config, with a safe built-in fallback."""
    override = os.environ.get("PRAKVERSE_SYSTEM_PROMPT")
    if override and override.strip():
        return override.strip()
    configured = _configured_prompt(config_path or PROJECT_ROOT / "config.yaml")
    return configured or DEFAULT_SYSTEM_PROMPT
