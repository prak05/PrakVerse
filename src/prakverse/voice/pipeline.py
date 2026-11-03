from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .speech import FasterWhisperSTT, PiperTTS, VoiceUnavailable
from .wake import WakeWordDetector


class VoicePipeline:
    """Wake-word or push-to-talk pipeline around injectable local adapters."""

    def __init__(
        self,
        transcriber: Any,
        speaker: Any,
        wake_detector: Any | None = None,
    ):
        self.transcriber = transcriber
        self.speaker = speaker
        self.wake_detector = wake_detector

    def process_audio(
        self,
        audio_path: str | Path,
        respond: Callable[[str], str],
        speak: bool = True,
    ) -> str:
        text = self.transcriber.transcribe(audio_path)
        if not text:
            return ""
        response = respond(text)
        if speak and response:
            self.speaker.speak(response)
        return response

    def stop_speaking(self) -> None:
        self.speaker.stop()


def build_local_pipeline(
    model_size: str = "base",
    whisper_device: str = "cpu",
    piper_model: str | Path | None = None,
) -> VoicePipeline:
    return VoicePipeline(
        FasterWhisperSTT(model_size, whisper_device),
        PiperTTS(piper_model),
        WakeWordDetector(),
    )
