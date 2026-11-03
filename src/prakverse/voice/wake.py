from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .speech import VoiceUnavailable


class WakeWordDetector:
    """Optional openWakeWord adapter; tests can inject a detector object."""

    def __init__(self, wake_word: str = "hey_priyumvada", detector: Any = None):
        self.wake_word = wake_word
        if detector is not None:
            self._detector = detector
            return
        try:
            from openwakeword.model import Model
        except ImportError as error:
            raise VoiceUnavailable(
                "Install voice dependencies with: pip install -e '.[voice]'"
            ) from error
        self._detector = Model()

    def detected(self, audio_frames: Iterable[Any]) -> bool:
        for frame in audio_frames:
            scores = self._detector.predict(frame)
            if float(scores.get(self.wake_word, 0.0)) >= 0.5:
                return True
        return False
